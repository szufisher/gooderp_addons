# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016  开阖软件(<http://www.osbzr.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models, api
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from datetime import datetime
from odoo.tools import float_compare, float_is_zero


class ZtTestPlan(models.Model):
	_name = "zt.test.plan"
	_inherit = ['mail.thread']
	_description = "test plan"
	# _order = 'date desc, id desc'

	name = fields.Char(u'名称', required=True, index=True, copy=False, help=u"名称")
	project_id = fields.Many2one('zt.project', u'项目')
	product_id = fields.Many2one('zt.product', u'产品')
	build_id = fields.Many2one('zt.build', index=True, string=u'构建版本')
	owner = fields.Many2one('res.users', u'测试负责人', required=True, help=u'测试负责人')
	pri = fields.Selection([('1', u'高'), ('2', u'中'), ('3', u'低')], U'优先级', default='2')
	begin = fields.Date('开始日期')
	end = fields.Date('结束日期')
	desc = fields.Text(u'测试报告')
	status = fields.Selection([('blocked', u'阻塞'), ('doing', '进行中'), ('wait', u'等待'), ('done', u'已完成')],
							  string=u'测试状态', default='wait')
	case_ids = fields.Many2many('zt.case', 'test_plan_case_rel', 'test_plan_id', 'case_id', string=u'测试剧本')
	summary = fields.Text(u'测试总结')
	remarks = fields.Text(u'备注')

	@api.multi
	def action_open_wizard_form(self):
		self.ensure_one()
		action = self.env.context.get('action', '')
		name = self.env.context.get('name', 'test plan')
		if action:
			result = {
				'name': name,
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'zt.test.plan',
				'target': 'new',
				'res_id': self.id,
				'view_id': self.env.ref('zt_project.zt_%s_test_plan_form' % action).id or 0
			}
			return result

	@api.multi
	def action_wizard(self):
		self.ensure_one()
		action = self.env.context.get('action', '')
		name = self.env.context.get('name', '')
		if action == 'start':
			self.status = 'doing'
		elif action == 'finish':
			self.status = 'done'
		subject = '%s test plan' % name
		self.message_post(self.remarks, subject)
		self.remarks = ''


class ZtCaseType(models.Model):
	_name = 'zt.case.type'
	_description = 'Case Type'

	name = fields.Char(u'测试剧本类型', required=True)


class ZtCase(models.Model):
	_name = 'zt.case'
	_description = 'test case'
	_inherit = ['mail.thread']

	@api.depends('story_id.version', 'story_id.status')
	def _compute_story_version_changed(self):
		for case in self:
			if case.story_id.status == 'active' and case.story_id.version != case.story_version:
				case.story_version_changed = True
			else:
				case.story_version_changed = False

	product_id = fields.Many2one('zt.product', index=True, string=u'产品')
	module_id = fields.Many2one('zt.module', index=True, string=u'模块')
	story_id = fields.Many2one('zt.story', index=True, string=u'需求')
	story_version = fields.Integer(string=u'需求版本')
	story_version_changed = fields.Boolean(compute='_compute_story_version_changed', string=u'需求变更了？', search=True)
	name = fields.Char(u'描述', required=True, index=True)
	tag_ids = fields.Many2many('zt.tag', 'case_tag_rel', 'case_id', 'tag_id', string=u'关键字')
	type = fields.Many2one('zt.case.type', string=u'测试类型')
	pri = fields.Selection([('1', u'高'), ('2', u'中'), ('3', '低')], U'优先级')
	precondition = fields.Text(u'前提条件')
	script_status = fields.Selection([(u'released', u'已发布 ')], u'状态')
	status = fields.Selection([('blocked', u'阻塞'), ('doing', '进行中'), ('wait', u'等待'), ('done', u'已完成')],
							  string=u'测试状态', default='wait')
	color = fields.Integer()
	last_runner = fields.Many2one('res.users', u'最后测试者')
	last_run_date = fields.Date(u'最后测试日期')
	last_run_result = fields.Text(u'最近测试结果')
	from_bug_id = fields.Many2one('zt.bug', u'来源于缺陷')
	version = fields.Integer()
	step_ids = fields.One2many('zt.case.step', 'case_id')
	remarks = fields.Text(u'备注')
	test_plan_id = fields.Many2one('zt.test.plan', string=u'所属测试计划')
	test_run_ids = fields.One2many('zt.test.run', 'case_id', string=u'测试结果')

	@api.multi
	def action_confirm_story_change(self):
		for task in self:
			if task.story_id:
				task.story_version = task.story_id.version

	@api.multi
	def action_open_wizard_form(self):
		self.ensure_one()
		action = self.env.context.get('action', '')
		name = self.env.context.get('name', 'case')
		if action:
			result = {
				'name': name,
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'zt.case',
				'target': 'new',
				'res_id': self.id,
				'view_id': self.env.ref('zt_project.zt_%s_test_plan_form' % action).id or 0
			}
			return result

	@api.multi
	def action_record_test_result(self):
		self.ensure_one()
		test_run_id = self.test_run_ids.create({'case_id': self.id,
												'assigned_to_id': self.env.uid
												})
		if test_run_id:
			obj_test_result = self.env['zt.test.result']
			[obj_test_result.create({'test_run_id': test_run_id.id,
									 'step_id': step.id}) for step in self.step_ids]
			result = {
				'name': '记录测试结果',
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'zt.test.run',
				'target': 'new',
				'res_id': test_run_id.id,
				'view_id': self.env.ref('zt_project.zt_test_run_form').id or 0
			}
			return result

	@api.multi
	def action_wizard(self):
		self.ensure_one()
		action = self.env.context.get('action', '')
		name = self.env.context.get('name', '')
		if action == 'start':
			self.status = 'doing'
		elif action == 'finish':
			self.status = 'done'
		subject = '%s case' % name
		self.message_post(self.remarks, subject)
		self.remarks = ''


class ZtCaseStep(models.Model):
	_name = 'zt.case.step'
	_description = 'case step'

	case_id = fields.Many2one('zt.case', u'测试剧本')
	version = fields.Integer(related='case_id.version')
	name = fields.Text(u'步骤描述', required=True)
	expect = fields.Text(u'预期结果', required=True)


class ZtTestRun(models.Model):
	_name = 'zt.test.run'
	_description = 'test run'

	case_id = fields.Many2one('zt.case', u'测试剧本')
	test_plan_id = fields.Many2one('zt.test.plan', related='case_id.test_plan_id', string=u'所属测试计划')
	case_version = fields.Integer(related='case_id.version')
	assigned_to_id = fields.Many2one('res.users', u'分派给')
	last_runner = fields.Many2one('res.users', u'最后测试者')
	last_run_date = fields.Date(u'最后测试日期')
	last_run_result = fields.Text(u'最近测试结果')
	status = fields.Selection([('active', u'进行中')])
	result_ids = fields.One2many('zt.test.result', 'test_run_id')


class ZtTestResult(models.Model):
	_name = 'zt.test.result'
	_description = 'test result'

	test_run_id = fields.Many2one('zt.test.run', u'测试执行')
	case_id = fields.Many2one('zt.case', related='test_run_id.case_id', string=u'测试剧本')
	version = fields.Integer(related='case_id.version')
	step_id = fields.Many2one('zt.case.step')
	name = fields.Text(u'步骤描述', related='step_id.name')
	expect = fields.Text(u'预期结果', related='step_id.expect')
	actual = fields.Text(u'实际结果')
	result = fields.Boolean(u'测试结论')
	last_runner = fields.Many2one('res.users', u'最后测试者')
	date = fields.Date(u'测试日期')


class ZtBug(models.Model):
	_name = 'zt.bug'
	_inherit = ['mail.thread']
	_description = 'bug'

	product_id = fields.Many2one('zt.product', index=True, string=u'所属产品')
	module_id = fields.Many2one('zt.module', index=True, string=u'所属模块')
	product_plan_id = fields.Many2one('zt.product.plan')
	project_id = fields.Many2one('zt.project', index=True, string=u'所属项目')
	story_id = fields.Many2one('zt.story', u'相关需求')
	story_version = fields.Integer(related='story_id.version')
	task_id = fields.Many2one('zt.task')
	to_task_id = fields.Many2one('zt.task')
	to_story_id = fields.Many2one('zt.story', u'转至需求')
	name = fields.Char('缺陷描述', index=True, required=True)
	tag_ids = fields.Many2many('zt.tag', 'bug_tag_rel', 'bug_id', 'tag_id', string=u'关键字')
	type = fields.Many2one('zt.bug.type', string=u'bug类型')
	pri = fields.Selection([('1', u'高'), ('2', u'中'), ('3', u'低')], U'优先级')
	found = fields.Text(u'缺陷源')
	steps = fields.Html(u'重现步骤')
	confirmed = fields.Boolean(u'已确认?')
	status = fields.Selection([('active', u'进行中'), ('resolved', u'已解决'),
							   ('closed', u'已关闭')], u'缺陷状态', default='active')
	activated_count = fields.Integer(u'激活次数')
	color = fields.Integer()
	assigned_to_id = fields.Many2one('res.users', index=True, string=u'指派给')
	assigned_date = fields.Date(u'指派日期')
	resolved_by_id = fields.Many2one('res.users', u'由谁解决')
	resolved_date = fields.Date(u'完成日期')
	resolution = fields.Text(u'解决方案')
	affected_build_ids = fields.Many2many('zt.build', 'bug_build_rel_a', 'bug_id', 'build_id', string=u'影响版本')
	resolved_build_ids = fields.Many2many('zt.build', 'bug_build_rel_r', 'bug_id', 'build_id', string=u'解决版本')
	build_id = fields.Many2one('zt.build', string=u'解决版本')
	closed_by_id = fields.Many2one('res.users', u'由谁关闭')
	closed_date = fields.Date(u'关闭日期')
	closed_reason = fields.Text(u'关闭原因')
	case_id = fields.Many2one('zt.case', string=u'测试剧本')
	case_version = fields.Integer(related='case_id.version')
	test_result = fields.Text(u'测试结果')
	test_plan_id = fields.Many2one('zt.test.plan', string=u'所属测试计划')
	duplicate_bug_id = fields.Many2one('zt.bug', string=u'重复缺陷号')
	link_bug_ids = fields.Many2many('zt.bug', 'bug_bug_rel', 'bug_id1', 'bug_id2', string=u'相关缺陷')
	remarks = fields.Text(u'备注')
	follower_ids = fields.Many2many('res.users', 'bug_user_rel', 'bug_id', 'user_id', string=u'抄送给')

	@api.multi
	def action_open_wizard_form(self):
		self.ensure_one()
		action = self.env.context.get('action', '')
		name = self.env.context.get('name', 'bug')
		if action:
			result = {
				'name': name,
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form'
			}
			if action == 'create_story':
				result.update({
					'res_model': 'zt.story',
					'domain': [('from_bug_id', '=', self.id)],
					'context': {'default_from_bug_id': self.id},
					'target': 'current'
				})
			else:
				view = self.env.ref('zt_project.zt_%s_bug_form' % action)
				result.update({
					'res_model': 'zt.bug',
					'target': 'new',
					'res_id': self.id
				})
				if view:
					result.update({
						'view_id': view.id,
					})
			return result

	@api.multi
	def action_wizard(self):
		self.ensure_one()
		action = self.env.context.get('action', '')
		name = self.env.context.get('name', '')
		if action == 'confirm':
			self.confirmed = True
		elif action == 'assign':
			if not self.assigned_date:
				self.assigned_date = fields.Datetime.now()
		elif action == 'resolve':
			self.confirmed = True
			self.status = 'resolved'
			if not self.resolved_date_date:
				self.resolved_date = fields.Datetime.now()
			if not self.resolved_by_id:
				self.resolved_by_id = self.env.uid
		elif action == 'close':
			self.status = 'closed'
			self.closed_date = fields.Datetime.now()
			self.closed_by_id = self.env.uid
		elif action == 'activate':
			self.status = 'active'
			self.activated_count += 1
		subject = '%s bug' % name
		self.message_post(self.remarks, subject)
		self.remarks = ''


class ZtBugType(models.Model):
	_name = 'zt.bug.type'
	_description = 'bug type'

	name = fields.Char(u'缺陷类型', required=True, index=True)


class ZtBuild(models.Model):
	_name = 'zt.build'
	_description = 'build'

	product_id = fields.Many2one('zt.product', index=True, required=True, string=u'产品')
	project_id = fields.Many2one('zt.project', index=True, string=u'项目')
	name = fields.Char(u'名称', required=True, index=True)
	scm_path = fields.Char(u'版本库路径')
	file_path = fields.Char(u'源文件路径')
	date = fields.Date(u'日期')
	story_ids = fields.Many2many('zt.story', 'build_story_rel', 'build_id', 'story_id', string=u'关联需求')
	bug_ids = fields.One2many('zt.bug', 'build_id', string=u'关联缺陷')
	builder_id = fields.Many2one('res.users', string=u'构建者')
	desc = fields.Html(u'任务描述')


class ZtStory(models.Model):
	_inherit = 'zt.story'

	@api.depends('bug_ids')
	def _compute_bug(self):
		for story in self:
			story.bug_count = len(story.bug_ids.ids)

	@api.depends('case_ids')
	def _compute_case(self):
		for story in self:
			story.case_count = len(story.case_ids.ids)

	bug_ids = fields.One2many('zt.bug', 'story_id')
	bug_count = fields.Integer('相关bug数', compute='_compute_bug')
	case_ids = fields.One2many('zt.case', 'story_id')
	case_count = fields.Integer('相关测试剧本数', compute='_compute_case')

	@api.multi
	def action_view_bug(self):
		"""
		This function returns an action that display existing task of given purchase order ids( linked/computed via buy.receipt).
		When only one found, show the invoice immediately.
		"""
		self.ensure_one()
		if self.bug_count == 0:
			return False
		action = {
			'name': u'bug',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			# 'view_mode': 'form',
			'res_model': 'zt.bug',
			'view_id': False,
			'target': 'current',
		}
		bug_ids = self.bug_ids.ids
		# choose the view_mode accordingly
		if len(bug_ids) > 1:
			action['domain'] = "[('id','in',[" + ','.join(map(str, bug_ids)) + "])]"
			action['view_mode'] = 'tree, form'
		elif len(bug_ids) == 1:
			action['view_mode'] = 'form',
			action['views'] = [(False, 'form')]
			action['res_id'] = bug_ids and bug_ids[0] or False
		return action

	@api.multi
	def action_view_case(self):
		"""
		This function returns an action that display existing task of given purchase order ids( linked/computed via buy.receipt).
		When only one found, show the invoice immediately.
		"""
		self.ensure_one()
		if self.case_count == 0:
			return False
		action = {
			'name': u'测试剧本',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'res_model': 'zt.case',
            'view_mode': 'form',
			'view_id': False,
			'target': 'current',
		}
		case_ids = self.case_ids.ids
		# choose the view_mode accordingly
		if len(case_ids) > 1:
			action['domain'] = "[('id','in',[" + ','.join(map(str, case_ids)) + "])]"
			action.update({'view_mode': 'tree,form'})
		elif len(case_ids) == 1:
			action['views'] = [(False, 'form')]
			action['res_id'] = case_ids and case_ids[0] or False
		return action
