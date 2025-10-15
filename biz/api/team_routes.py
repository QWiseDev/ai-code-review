"""
团队管理API路由
提供团队创建、更新、删除和成员管理功能
"""
from    flask    import    request
from    flask_jwt_extended    import    jwt_required

from    biz.service.review_service    import    ReviewService
from    biz.utils.api_helpers    import    ApiResponse,    Validator,    handle_api_errors,    log_api_call,    ValidationError
from    biz.utils.log    import    logger


def    register_team_routes(app):
                """注册团队管理相关路由"""

                @app.route('/api/teams',    methods=['GET'])
                @jwt_required()
                @log_api_call
                @handle_api_errors('get_teams')
                def    get_teams():
                                """获取团队列表"""
                                include_members    =    request.args.get('include_members',    '1')    !=    '0'
                                teams    =    ReviewService.list_teams(include_members=include_members)
                                logger.info(f"获取团队列表成功，共    {len(teams)}    个团队")
                                return    ApiResponse.success(data=teams)

                @app.route('/api/teams/<int:team_id>',    methods=['GET'])
                @jwt_required()
                @log_api_call
                @handle_api_errors('get_team_detail')
                def    get_team_detail(team_id:    int):
                                """获取团队详情"""
                                include_members    =    request.args.get('include_members',    '1')    !=    '0'
                                team    =    ReviewService.get_team(team_id,    include_members=include_members)
                                if    not    team:
                                                raise    FileNotFoundError('团队不存在')
                                return    ApiResponse.success(data=team)

                @app.route('/api/teams',    methods=['POST'])
                @jwt_required()
                @log_api_call
                @handle_api_errors('create_team')
                def    create_team():
                                """创建团队"""
                                data    =    request.get_json()    or    {}
                                name    =    (data.get('name')    or    '').strip()
                                webhook_url    =    data.get('webhook_url')

                                #    验证团队名称
                                is_valid,    error_msg    =    Validator.validate_team_name(name)
                                if    not    is_valid:
                                                raise    ValidationError(error_msg)

                                #    验证    Webhook    URL
                                if    webhook_url    and    not    Validator.validate_webhook_url(webhook_url):
                                                raise    ValidationError('Webhook    URL    格式无效，请提供有效的    HTTP/HTTPS    URL')

                                team    =    ReviewService.create_team(
                                                name=name,
                                                webhook_url=webhook_url,
                                                description=data.get('description')
                                )
                                if    not    team:
                                                raise    ValueError('团队创建失败')

                                logger.info(f"团队创建成功:    {name}    (ID:    {team.get('id')})")
                                return    ApiResponse.success(data=team,    message='团队创建成功',    code=201)

                @app.route('/api/teams/<int:team_id>',    methods=['PUT'])
                @jwt_required()
                @log_api_call
                @handle_api_errors('update_team')
                def    update_team(team_id:    int):
                                """更新团队信息"""
                                data    =    request.get_json()    or    {}
                                name    =    data.get('name')
                                webhook_url    =    data.get('webhook_url')

                                #    验证团队名称（如果提供）
                                if    name    is    not    None:
                                                is_valid,    error_msg    =    Validator.validate_team_name(name)
                                                if    not    is_valid:
                                                                raise    ValidationError(error_msg)

                                #    验证    Webhook    URL（如果提供）
                                if    webhook_url    is    not    None    and    webhook_url.strip():
                                                if    not    Validator.validate_webhook_url(webhook_url):
                                                                raise    ValidationError('Webhook    URL    格式无效，请提供有效的    HTTP/HTTPS    URL')

                                team    =    ReviewService.update_team(
                                                team_id=team_id,
                                                name=name,
                                                webhook_url=webhook_url,
                                                description=data.get('description')
                                )
                                if    not    team:
                                                raise    FileNotFoundError('团队不存在')

                                logger.info(f"团队更新成功:    ID    {team_id}")
                                return    ApiResponse.success(data=team,    message='团队更新成功')

                @app.route('/api/teams/<int:team_id>',    methods=['DELETE'])
                @jwt_required()
                @log_api_call
                @handle_api_errors('delete_team')
                def    delete_team(team_id:    int):
                                """删除团队"""
                                deleted    =    ReviewService.delete_team(team_id)
                                if    not    deleted:
                                                raise    FileNotFoundError('团队不存在')

                                logger.info(f"团队删除成功:    ID    {team_id}")
                                return    ApiResponse.success(message='团队删除成功')

                @app.route('/api/teams/<int:team_id>/members',    methods=['POST'])
                @jwt_required()
                @log_api_call
                @handle_api_errors('add_team_members')
                def    add_team_members(team_id:    int):
                                """批量添加团队成员"""
                                data    =    request.get_json()    or    {}
                                authors    =    data.get('authors')

                                #    验证作者列表
                                is_valid,    error_msg    =    Validator.validate_authors(authors)
                                if    not    is_valid:
                                                raise    ValidationError(error_msg)

                                added    =    ReviewService.add_team_members(team_id,    authors)
                                team    =    ReviewService.get_team(team_id,    include_members=True)
                                if    not    team:
                                                raise    FileNotFoundError('团队不存在')

                                logger.info(f"团队    {team_id}    添加成员成功，新增    {added}    人")
                                return    ApiResponse.success(
                                                data={'added':    added,    'team':    team},
                                                message=f'成功添加    {added}    个成员'
                                )

                @app.route('/api/teams/<int:team_id>/members/<author>',    methods=['DELETE'])
                @jwt_required()
                @log_api_call
                @handle_api_errors('remove_team_member')
                def    remove_team_member(team_id:    int,    author:    str):
                                """移除团队成员"""
                                if    not    author    or    not    author.strip():
                                                raise    ValidationError('成员名称不能为空')

                                removed    =    ReviewService.remove_team_member(team_id,    author)
                                if    not    removed:
                                                raise    FileNotFoundError('成员不存在或团队不存在')

                                team    =    ReviewService.get_team(team_id,    include_members=True)
                                logger.info(f"团队    {team_id}    移除成员成功:    {author}")
                                return    ApiResponse.success(data=team,    message='成员移除成功')
