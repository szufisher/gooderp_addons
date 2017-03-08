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
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import float_compare, float_is_zero


class ZtProject(models.Model):
    _name = "zt.project"
    _inherit = ['mail.thread']
    _description = "project"
    _order = "sequence, begin, name, id"
    # _order = 'date desc, id desc'

    name = fields.Char(u'项目名称', required=True, index=True, copy=False, help=u"项目", track_visibility='always')
    code = fields.Char(u'项目代号', required=True, index=True, copy=False, help=u"代号")
    type = fields.Char(u'项目类型', help=u"类型")
    parent = fields.Many2one('zt.project', u'上级项目')
    desc = fields.Html(u'项目描述', required=True)
    pri = fields.Selection([('0', '一般'), ('1', '高')], default='0', index=True, string=u'优先级')
    begin = fields.Date(u'开始日期', default=fields.Datetime.now, index=True, copy=False)
    end = fields.Date(u'结束日期', index=True, copy=False)
    days = fields.Integer(u'可用工作日')
    status = fields.Selection([('active', 'active'), ('closed', 'closed')])
    stage = fields.Selection([('1', '1'), ('2', '2')])
    cancelled_by_id = fields.Many2one('res.users', u'评审者')
    cancelled_date = fields.Date(u'评审日期')
    closed_by_id = fields.Many2one('res.users', u'关闭者')
    closed_date = fields.Date(u'关闭日期')
    po = fields.Many2one('res.users', u'产品负责人', help=u'产品负责人')
    pm = fields.Many2one('res.users', u'项目负责人', help=u'项目负责人')
    qd = fields.Many2one('res.users', u'测试负责人', help=u'测试负责人')
    rd = fields.Many2one('res.users', u'开发负责人', help=u'发布负责人')
    member_ids = fields.One2many('zt.team', 'project_id', string=u'项目团队')
    acl = fields.Selection([('open', u'默认设置，有项目视图权限即可访问'),
                            ('private', u'私有项目，只有项目相关负责人和项目团队成员能够访问'),
                            ('custom', u'自定义白名单，团队成员和白名单成员可以访问')],
                           default='open', string=u'访问控制')
    whitelist = fields.Many2many('res.users', 'project_user_rel', 'project_id', 'user_id')
    sequence = fields.Integer(u'排序', index=True, default=10)
    story_ids = fields.Many2many('zt.story', 'zt_project_story_rel', 'project_id', 'story_id', string=u'相关需求')
    task_ids = fields.Many2many('zt.task', 'zt_project_task_rel', 'project_id', 'task_id', string=u'项目任务')
    product_ids = fields.Many2many('zt.product', 'zt_project_product_rel', 'project_id', 'product_id', string=u'相关产品')

    @api.constrains('begin', 'end')
    def _check_dates(self):
        if any(self.filtered(lambda task: task.begin and task.end and task.begin > task.end)):
            return ValidationError(_('结束日期应该晚于开始日期'))


class ZtProjectProduct(models.Model):
    _name = 'zt.project.product'
    _description = 'project product'

    project_id = fields.Many2one('zt.project', u'项目')
    product_id = fields.Many2one('zt.product', u'产品')


class ZtProjectStory(models.Model):
    _name = "zt.project.story"
    _inherit = ['mail.thread']
    _description = "project requirement"
    # _order = 'date desc, id desc'

    project_id = fields.Many2one('zt.project', u'项目')
    product_id = fields.Many2one('zt.product', u'产品')
    story_id = fields.Many2one('zt.story', u'需求')
    version = fields.Integer(related='story_id.version')


class ZtTeam(models.Model):
    _name = 'zt.team'
    _description = 'project team'

    project_id = fields.Many2one('zt.project', u'项目')
    user_id = fields.Many2one('res.users', u'团队成员')
    role = fields.Char(u'项目角色', required=True)
    join = fields.Date(u'加盟日期', required=True)
    days = fields.Float(u'工作天数', required=True)
    hours = fields.Float(u'每天工作小时数', required=True)


class ZtTaskType(models.Model):
    _name = 'zt.task.type'
    _description = 'task type'

    name = fields.Char(u'任务类型', required=True)


class ZtTask(models.Model):
    _name = 'zt.task'
    _inherit = ['mail.thread']
    _description = 'task'

    @api.depends('story_id.version', 'story_id.status')
    def _compute_story_version_changed(self):
        for task in self:
            if task.story_id.status == 'active' and task.story_id.version != task.story_version:
                task.story_version_changed = True
            else:
                task.story_version_changed = False

    project_id = fields.Many2one('zt.project', u'所属项目')
    product_id = fields.Many2one('zt.product', u'所属产品')
    module_id = fields.Many2one('zt.module', u'所属模块')
    story_id = fields.Many2one('zt.story', u'相关需求')
    story_version = fields.Integer()
    story_version_changed = fields.Boolean(compute='_compute_story_version_changed', string=u'需求变更了？', search=True)
    from_bug_id = fields.Many2one('zt.bug', u'缺陷')
    name = fields.Char(u'任务名称', required=True, index=True, copy=False, help=u"任务名称")
    tag_ids = fields.Many2many('zt.tag', 'task_tag_rel', 'task_id', 'tag_id', string=u'关键字')
    type = fields.Many2one('zt.task.type', u'任务类型')
    pri = fields.Selection([('0', '一般'), ('1', '高')], default='0', index=True, string=u'优先级')
    estimate = fields.Float('预计工时')
    consumed = fields.Float('总消耗')
    left = fields.Float('预计剩余')
    deadline = fields.Date('到期日')
    status = fields.Selection([('wait', u'未开始'), ('doing', u'进行中'), ('done', u'已完成'),
                               ('pause', u'暂停'), ('cancel', u'取消'), ('close', u'已关闭')],
                              default='wait', string=u'状态')
    desc = fields.Html(u'任务描述', required=True)
    color = fields.Integer()
    assigned_to_id = fields.Many2one('res.users', u'指派给')
    assigned_date = fields.Date(u'指派日期')
    est_start = fields.Date(u'预计开始日期')
    real_start = fields.Date(u'实际开始日期')
    finished_by_id = fields.Many2one('res.users', u'由谁完成')
    finished_date = fields.Date(u'完成日期')
    cancelled_by_id = fields.Many2one('res.users', u'由谁取消')
    cancelled_date = fields.Date(u'取消日期')
    closed_by_id = fields.Many2one('res.users', u'由谁关闭')
    closed_date = fields.Date(u'关闭日期')
    closed_reason = fields.Text(u'关闭原因')
    follower_ids = fields.Many2many('res.users', 'task_user_rel', 'task_id', 'user_id', string=u'抄送给')
    remarks = fields.Text(u'备注')

    @api.model
    def create(self, vals):
        if vals.get('assigned_to_id') and not vals.get('assigned_date'):
            vals['assigned_date'] = fields.Datetime.now()
        story_id = vals.get('story_id', '')
        if story_id:
            vals['story_version'] = self.story_id.browse(story_id).version
        result = super(ZtTask, self).create(vals)
        return result

    @api.multi
    def write(self, vals):
        if vals.get('finished_by_id') and not vals.get('finished_date'):
            vals['finished_date'] = fields.Datetime.now()
        if vals.get('cancelled_by_id') and not vals.get('cancelled_date'):
            vals['cancelled_date'] = fields.Datetime.now()
        if vals.get('closed_by_id') and not vals.get('closed_date'):
            vals['closed_date'] = fields.Datetime.now()
        result = super(ZtTask, self).write(vals)
        return result

    @api.onchange('story_id')
    def onchange_story_id(self):
        if self.story_id:
            self.story_version = self.story_id.version
        else:
            self.story_version = 0

    @api.multi
    def action_confirm_story_change(self):
        for task in self:
            if task.story_id:
                task.story_version = task.story_id.version

    @api.multi
    def action_open_wizard_form(self):
        self.ensure_one()
        action = self.env.context.get('action', '')
        name = self.env.context.get('name', 'task')
        if action:
            result = {
                'name': name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form'
            }
            if action == 'create_effort':
                result.update({
                    'res_model': 'zt.effort',
                    'domain': [('task_id', '=', self.id)],
                    'context': {'default_task_id': self.id},
                    'target': 'current'
                })
            else:
                view = self.env.ref('zt_project.zt_%s_task_form' % action)
                result.update({
                    'res_model': 'zt.task',
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
        if action == 'start':
            self.status = 'doing'
            if not self.real_start:
                self.real_start = fields.Datetime.now()
        elif action == 'assign':
            if not self.assigned_date:
                self.assigned_date = fields.Datetime.now()
        elif action == 'finish':
            self.status = 'done'
            self.finished_by_id = self.env.uid
        elif action == 'pause':
            self.status = 'pause'
        elif action == 'close':
            self.status = 'close'
            self.closed_by_id = self.env.uid
            self.closed_date = fields.Datetime.now()
        elif action == 'continue':
            self.status = 'doing'
        elif action == 'cancel':
            self.status = 'cancel'
            self.cancelled_by_id = self.env.uid
        subject = '%s bug' % name
        self.message_post(self.remarks, subject)
        self.remarks = ''


class ZtTaskEstimate(models.Model):
    _name = 'zt.task.estimate'
    _description = 'task estimate'

    task_id = fields.Many2one('zt.task', index=True, string=u'任务')
    date = fields.Date(u'日期')
    consumed = fields.Float(u'已投入工时')
    left = fields.Float('剩余工时')
    user_id = fields.Many2one('res.users', u'责任人')
    work = fields.Char(u'工作内容')


class ZtEffort(models.Model):
    _name = 'zt.effort'
    _description = 'effort'

    user_id = fields.Many2one('res.users', required=True, string=u'用户')
    task_id = fields.Many2one('zt.task', string=u'任务')
    date = fields.Date(u'日期')
    begin = fields.Date(u'开始日期')
    end = fields.Date(u'结束日期')
    name = fields.Char(u'任务名称', required=True, index=True, copy=False, help=u"任务名称")
    desc = fields.Text(u'任务描述', required=True)
    type = fields.Char()
    status = fields.Selection([('1', '1'), ('2', '2')], string=u'状态')


class ZtStory(models.Model):
    _inherit = 'zt.story'

    @api.depends('task_ids')
    def _compute_task(self):
        for story in self:
            story.task_count = len(story.task_ids.ids)

    task_ids = fields.One2many('zt.task', 'story_id')
    task_count = fields.Integer('相关任务数', compute='_compute_task')

    @api.multi
    def action_view_task(self):
        self.ensure_one()
        if self.task_count == 0:
            return False
        action = {
            'name': u'任务',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'zt.task',
            'view_id': False,
            'target': 'current',
        }
        task_ids = self.task_ids.ids
        # choose the view_mode accordingly
        if len(task_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, task_ids)) + "])]"
            action.update({'view_mode': 'tree,form'})
        elif len(task_ids) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = task_ids and task_ids[0] or False
        return action
