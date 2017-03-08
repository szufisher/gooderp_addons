# -*- coding: utf-8 -*-
{
    'name': "GOODERP zt项目管理模块",
    'author': "szufisher@gmail.com",
    'website': "http://www.github.com/szufisher",
    'category': 'gooderp',
    "description":
    '''
                            该模块可以方便的软件开发项目。

                            通过创建产品，模块，产品开发计划，产品发布计划，产品需求。
                            通过创建项目，项目关联产品，项目关联需求，创建任务。
                            通过创建测试计划，测试剧本，执行测试，提交缺陷。

                            项目管理的报表有：
                                 xxx。
    ''',
    'version': '0.1',
    'depends': ['base','mail'],
    'data': [
        #'data/buy_data.xml',
        #'security/groups.xml',
        'views/zt_product_view.xml',
        'views/zt_project_view.xml',
        'views/zt_test_view.xml',
        'views/zt_product_action.xml',
        'views/zt_project_action.xml',
        'views/zt_test_action.xml',
        'views/zt_menu.xml',
        ],
    'demo': [
             #'data/buy_demo.xml',
             ],
}
