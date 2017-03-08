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
from odoo.models import NewId
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from datetime import datetime
from odoo.tools import float_compare, float_is_zero

REVIEW_CONCLUSION = [('pass', u'确认通过'),
					 ('cancel', u'撤销变更'),
					 ('clarify', u'有待明确'),
					 ('reject', u'拒绝')]


class ZtProduct(models.Model):
	_name = "zt.product"
	_inherit = ['mail.thread']
	_description = "product"
	_order = 'sequence'

	@api.depends('story_ids')
	def _compute_story(self):
		for product in self:
			product.story_count = len(product.story_ids.ids)

	name = fields.Char(u'产品名称', required=True, index=True, copy=False, help=u"产品")
	code = fields.Char(u'产品代号', required=True, index=True, copy=False, help=u"代号")
	type = fields.Char(u'产品类型', index=True, help=u"类型")
	desc = fields.Text(u'产品描述')
	po = fields.Many2one('res.users', u'产品负责人', help=u'产品负责人')
	qd = fields.Many2one('res.users', u'测试负责人', help=u'测试负责人')
	rd = fields.Many2one('res.users', u'开发负责人', help=u'发布负责人')
	status = fields.Selection([('active', u'正常'), ('closed', u'已结束')], string=u'状态', default='active')
	acl = fields.Selection([('open', u'默认设置，有产品视图权限即可访问'),
							('private', u'私有产品，只有产品相关负责人和项目团队成员能够访问'),
							('custom', u'自定义白名单，团队成员和白名单成员可以访问')],
						   default='open', string=u'访问控制')
	whitelist = fields.Many2many('res.users', 'product_user_rel', 'product_id', 'user_id')
	sequence = fields.Integer(string=u'排序', index=True, default=10)
	story_ids = fields.One2many('zt.story', 'product_id', string=u'需求')
	story_count = fields.Integer(compute='_compute_story')
	module_ids = fields.One2many('zt.module', 'product_id', string=u'模块')
	plan_ids = fields.One2many('zt.product.plan', 'product_id', string=u'发布计划')
	release_ids = fields.One2many('zt.release', 'product_id', string=u'发布')

	@api.multi
	def action_view_story(self):
		self.ensure_one()
		if self.story_count == 0:
			return False
		action = {
			'name': u'需求',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'zt.story',
			'view_id': False,
			'target': 'current',
		}
		story_ids = self.story_ids.ids
		# choose the view_mode accordingly
		if len(story_ids) > 1:
			action['domain'] = "[('id','in',[" + ','.join(map(str, story_ids)) + "])]"
			action['view_mode'] = 'tree, form'
		elif len(story_ids) == 1:
			action['views'] = [(False, 'form')]
			action['res_id'] = story_ids and story_ids[0] or False
		return action


class ZtModule(models.Model):
	_name = "zt.module"
	_description = "module"
	_order = 'sequence'

	product_id = fields.Many2one('zt.product', required=True, string=u'所属产品')
	name = fields.Char(u'模块名称', required=True, index=True, copy=False, help=u"模块名称")
	short = fields.Char(u'模块简称', index=True, copy=False, help=u"模块简称")
	parent = fields.Many2one('zt.module', string=u'父模块')
	type = fields.Char(u'模块类型', help=u"类型")
	owner = fields.Many2one('res.users', u'模块负责人')
	sequence = fields.Integer(string=u'排序', index=True, default=10)


class ZtProductPlan(models.Model):
	_name = "zt.product.plan"
	_inherit = ['mail.thread']
	_description = "product plan"

	product_id = fields.Many2one('zt.product', index=True, string=u'产品')
	name = fields.Char(u'计划名称', required=True, help=u"名称")
	desc = fields.Text(u'描述')
	begin = fields.Date(u'开始日期', required=True)
	end = fields.Date(u'结束日期', required=True)
	story_ids = fields.Many2many('zt.story', 'plan_story_rel', 'plan_id', 'story_id', string=u'相关需求')


class ZtRelease(models.Model):
	_name = "zt.release"
	_inherit = ['mail.thread']
	_description = "release"
	# _order = 'date desc, id desc'

	product_id = fields.Many2one('zt.product', string=u'产品')
	build_id = fields.Many2one('zt.build', index=True, string=u'构建版本')
	name = fields.Char(u'发布名称', required=True, index=True, copy=False, help=u"发布名称")
	date = fields.Date('发布日期', required=True)
	story_ids = fields.Many2many('zt.story', 'release_story_rel', 'release_id', 'story_id', string=u'相关需求')
	bug_ids = fields.Many2many('zt.bug', 'release_bug_rel', 'releas_id', 'bug_id', u'缺陷')
	left_bug_ids = fields.Many2many('zt.bug', 'release_left_bug_rel', 'release_id', 'bug_id', string=u'未解决的缺陷')
	status = fields.Selection([('active', u'进行中'), ('closed', u'已关闭')], string=u'发布状态')


class ZtStoryType(models.Model):
	_name = 'zt.story.type'
	_description = 'requirement type'

	name = fields.Char(u'需求类型', required=True)


class ZtStory(models.Model):
	_name = 'zt.story'
	_inherit = ['mail.thread']
	_description = 'requirement'

	def _review_conclusion(self):
		conclusion = REVIEW_CONCLUSION
		if self.status == 'draft':
			del conclusion[1]
		return conclusion

	def _compute_test_plan(self):
		for story in self:
			if isinstance(story.id, NewId):
				return
			test_tasks = self.env['zt.test.plan'].search([('case_ids.story_id.id', '=', story.id)])
			story.test_plan_ids = test_tasks

	@api.depends('stage_manual', 'test_plan_ids', 'test_plan_ids.status', 'test_plan_ids.case_ids.story_id',
				 'test_plan_ids.case_ids', 'task_ids', 'task_ids.type', 'task_ids.status',
				 'plan_ids', 'release_ids', 'project_ids')
	def _compute_stage(self):
		for story in self:
			if isinstance(story.id, NewId):
				story.stage = ''
				return
			if story.stage_manual:
				story.stage = story.stage_manual
			else:
				if len(story.release_ids):
					story.stage = 'released'
				else:
					test_tasks = story.test_plan_ids
					tested = len(test_tasks) and all(test_task.status == 'done' for test_task in test_tasks)
					testing = len(test_tasks) > 0
					develop_tasks = story.task_ids.filtered(lambda task: task.type.name == 'develop')
					developed = len(develop_tasks) > 0 and all(
						(task.status == 'done' or task.status == 'close') for task in develop_tasks)
					developing = len(develop_tasks) > 0
					if tested and developed:
						story.stage = 'tested'
					elif (tested and developing) or testing:
						story.stage = 'testing'
					elif developed:
						story.stage = 'developed'
					elif developing:
						story.stage = 'developing'
					elif len(self.env['zt.project'].search([('story_ids', '=', story.id)])):
						story.stage = 'projected'
					elif len(story.plan_ids):
						story.stage = 'planned'

	product_id = fields.Many2one('zt.product', string=u'所属产品')
	module_id = fields.Many2one('zt.module', u'所属模块')
	plan_id = fields.Many2one('zt.product.plan', u'所属计划')
	source = fields.Many2one('zt.story.source', u'需求来源', required=True)
	from_bug_id = fields.Many2one('zt.bug', u'缺陷')
	name = fields.Char(u'需求名称', required=True)
	spec = fields.Text(u'需求描述', required=True)
	verify = fields.Text(u'验收标准', required=True)
	tag_ids = fields.Many2many('zt.tag', 'story_tag_rel', 'story_id', 'tag_id', string=u'关键字')
	type = fields.Many2one('zt.story.type')
	pri = fields.Selection([('0', '一般'), ('1', '高')], U'优先级', default='0')
	estimate = fields.Float(u'预计工时', required=True)
	status = fields.Selection([('changed', u'变更中'), ('active', u'进行中'),
							   ('draft', u'待审批'), ('closed', u'已完成')], u'当前状态', default='draft')
	color = fields.Integer()
	stage = fields.Selection([('', u'未开始'), ('wait', u'待规划'), ('planned', u'已规划'), ('projected', u'已立项'),
							  ('developing', u'研发中'), ('developed', u'研发完毕'), ('testing', u'测试中'),
							  ('tested', u'测试完毕'), ('verified', u'已验收'), ('released', u'已发布')],
							 string=u'所处阶段', compute='_compute_stage', default='', store=True,
							 help=""" 1.如果需求没有关联到项目，也没有关联到计划，则需求的研发阶段是"未开始"。
								2.如果需求关联到了计划，还没有关联到项目中，则需求的研发阶段是"已计划"。
								3.如果需求关联到了项目中，但还没有分解任务，则需求的研发阶段是"已立项"。
								4.如果需求关联到了项目中，且进行了任务分解:
								如果有一个开发任务进行中，并且所有的测试任务还没有开始，需求的研发阶段为“研发中”。
								 如果所有的开发任务已经完成，并且所有的测试任务还没有开始，则为“研发完毕”。
								 如果有一个测试任务进行中，则视为“测试中”。
								 如果所有的测试任务已经结束，但还有一些开发任务没有结束，则视为"测试中"。
								 如果所有的测试任务已经结束，并且所有的开发任务已经结束，则视为"测试完毕"。
								5."验收"阶段是需要产品经理手工来进行确认的。
								6.产品→发布中关联的需求后，需求的研发阶段是“已发布”。""")
	stage_manual = fields.Selection([('', u'未开始'), ('wait', u'待规划'), ('planned', u'已规划'), ('projected', u'已立项'),
									 ('developing', u'研发中'), ('developed', u'研发完毕'), ('testing', u'测试中'),
									 ('tested', u'测试完毕'), ('verified', u'已验收'), ('released', u'已发布')],
									string=u'指定阶段')
	assigned_to_id = fields.Many2one('res.users', u'指派给')
	assigned_date = fields.Date(u'指派日期')
	no_need_review = fields.Boolean(u'不需要评审', default=False)
	reviewed_by_id = fields.Many2one('res.users', string=u'由谁评审')
	reviewed_by_ids = fields.Many2many('res.users', 'story_review_user_rel', 'story_id', 'user_id', string=u'参与评审者')
	reviewed_date = fields.Date(u'评审日期')
	review_conclusion = fields.Selection('_review_conclusion', string=u'评审结果')
	closed_by_id = fields.Many2one('res.users', u'由谁关闭')
	closed_date = fields.Date(u'关闭日期')
	close_reason = fields.Selection([('complete', u'已完成'),
									 ('breakdown', u'已细分'),
									 ('duplicate', u'重复'),
									 ('postpone', u'延期'),
									 ('reject', u'不做'),
									 ('cancel', u'已取消'),
									 ('bydesign', u'设计如此')], string=u'关闭原因')
	to_bug_id = fields.Many2one('zt.bug', u'转至缺陷')
	parent_id = fields.Many2one('zt.story', string=u'父需求', index=True)
	child_ids = fields.One2many('zt.story', 'parent_id', string=u'子需求')
	# link_story_ids = fields.One2many('zt.story', 'id', u'关联需求')
	duplicate_story_id = fields.Many2one('zt.story', u'重复需求')
	version = fields.Integer(u'版本', default=1)
	plan_ids = fields.Many2many('zt.product.plan', 'plan_story_rel', 'story_id', 'plan_id', string=u'相关发布计划')
	release_ids = fields.Many2many('zt.release', 'release_story_rel', 'story_id', 'release_id', string=u'相关发布')
	remarks = fields.Text(u'备注')
	story_history_ids = fields.One2many('zt.story.history', 'story_id')
	project_ids = fields.Many2many('zt.project', 'zt_project_story_rel', 'story_id', 'project_id', string=u'相关项目')
	test_plan_ids = fields.Many2many('zt.test.plan', compute='_compute_test_plan', string=u'测试计划')

	@api.multi
	def name_get(self):
		return [(story.id, '%s /%s' % (story.name, story.version)) for story in self]

	@api.model
	def create(self, vals):
		if vals.get('no_need_review', ''):
			vals['status'] = 'active'
		result = super(ZtStory, self).create(vals)
		return result

	@api.multi
	def action_open_wizard_form(self):
		self.ensure_one()
		action = self.env.context.get('action', '')
		name = self.env.context.get('name', '需求')
		if action:
			view = self.env.ref('zt_project.zt_%s_story_form' % action)
			if view:
				action = {
					'name': name,
					'type': 'ir.actions.act_window',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'zt.story',
					'view_id': view.id,
					'target': 'new',
					'res_id': self.id
				}
				return action

	@api.multi
	def action_change_story(self):
		for bug in self:
			if bug.no_need_review:
				bug.status = 'active'
			else:
				bug.status = 'changed'
			bug.story_history_ids.create({'story_id': bug.id,
										  'version': self.env.context.get('version', ''),
										  'name': self.env.context.get('story_name', ''),
										  'spec': self.env.context.get('spec', ''),
										  'verify': self.env.context.get('verify', '')})
			bug.version += 1
			if bug.remarks:
				bug.message_post(bug.remarks, subject='story changed')
				bug.remarks = ''

	@api.multi
	def action_review_story(self):
		for bug in self:
			if bug.review_conclusion == 'pass':
				bug.status = 'active'
			elif bug.review_conclusion == 'reject':
				bug.status = 'closed'
			elif bug.review_conclusion == 'cancel' and bug.status == 'changed':
				bug.status = 'active'
				bug_old = bug.story_history_ids[0]
				bug.write({'version': bug_old.version,
						   'name': bug_old.name,
						   'spec': bug_old.spec,
						   'verify': bug_old.verify,
						   'status': 'active'})
				bug.story_history_ids[0].unlink()
			if bug.remarks:
				bug.message_post(bug.remarks, subject='story reviewed')
				bug.remarks = ''

	@api.multi
	def action_close_story(self):
		for bug in self:
			bug.status = 'closed'
			if bug.remarks:
				bug.message_post(bug.remarks, subject='story closed')
				bug.remarks = ''

	@api.multi
	def action_activate_story(self):
		for bug in self:
			bug.status = 'active'
			if bug.remarks:
				bug.message_post(bug.remarks, subject='story activated')
				bug.remarks = ''

	@api.multi
	def action_case(self):

		return {
			'name': _('测试剧本'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'zt.case',
			'views': [(False, 'tree'), (False, 'form')],
			'domain': [('story_id', '=', self.id)],
			# 'target': 'current',
			'context': {
				'default_story_id': self.id
			},
		}


class ZtStoryHistory(models.Model):
	_name = 'zt.story.history'
	_description = 'story version history'
	_order = 'story_id, version desc'

	story_id = fields.Many2one('zt.story', string=u'需求')
	version = fields.Integer()
	name = fields.Char(u'需求名称')
	spec = fields.Text(u'详细需求描述')
	verify = fields.Text(u'验收标准')


class ZtStorySource(models.Model):
	_name = 'zt.story.source'
	_description = 'story source'

	name = fields.Char(u'需求来源')


class ZtTag(models.Model):
	_name = 'zt.tag'
	_description = 'tag keyword'

	name = fields.Char(u'关键字', required=True)
