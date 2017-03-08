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


class ZtStory(models.TransientModel):
    _name = 'zt.story.wizard'

    _description = 'requirement'

    @api.depends('task_ids')
    def _compute_stage(self):
        pass

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
    pri = fields.Selection([('0', '高'), ('1', '中'), ('3', '低')], U'优先级', default='0')
    estimate = fields.Float(u'预计工时', required=True)
    status = fields.Selection([('changed', u'变更中'), ('active', u'进行中'),
                               ('draft', u'待审批'), ('closed', u'已完成')], u'当前状态', default='draft')
    color = fields.Integer()
    stage = fields.Selection([('', u'未开始'), ('wait', u'待规划'), ('planned', u'已规划'), ('projected', u'已立项'),
                              ('developing', u'研发中'), ('developed', u'研发完毕'), ('testing', u'测试中'),
                              ('tested', u'测试完毕'), ('verified', u'已验收'), ('released', u'已发布')],
                             string=u'所处阶段',
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
    assigned_to_id = fields.Many2one('res.users', u'指派给')
    assigned_date = fields.Date(u'指派日期')
    no_need_review = fields.Boolean(u'不需要评审', default=False)
    reviewed_by_id = fields.Many2one('res.users', string=u'由谁评审')
    reviewed_by_ids = fields.Many2many('res.users', 'story_review_user_rel', 'story_id', 'user_id', string=u'参与评审者')
    reviewed_date = fields.Date(u'评审日期')
    review_conclusion = fields.Selection([('pass', u'确认通过'),
                                          ('cancel', u'撤销变更'),
                                          ('clarify', u'有待明确'),
                                          ('reject', u'拒绝')], string=u'评审结果')
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
    plan_ids = fields.Many2many('zt.product.plan', 'release_story_rel', 'story_id', 'release_id', string=u'相关发布计划')
    release_ids = fields.Many2many('zt.release', 'plan_story_rel', 'story_id', 'plan_id', string=u'相关发布')
    remarks = fields.Text(u'备注')
    story_history_ids = fields.One2many('zt.story.history', 'story_id')