from dotenv import load_dotenv

load_dotenv("conf/.env")

import atexit
import json
import os
import traceback
from datetime import datetime
from urllib.parse import urlparse

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import hashlib
import hmac
import base64
import time

from biz.gitlab.webhook_handler import slugify_url
from biz.queue.worker import handle_merge_request_event, handle_push_event, handle_github_pull_request_event, \
    handle_github_push_event
from biz.service.review_service import ReviewService
from biz.utils.im import notifier
from biz.utils.im.team_webhook import TeamWebhookNotifier
from biz.utils.log import logger
from biz.utils.queue import handle_queue
from biz.utils.reporter import Reporter
from    biz.utils.api_helpers    import    ApiResponse,    Validator,    handle_api_errors,    log_api_call,    ValidationError

from biz.utils.config_checker import check_config
from biz.utils.time_utils import convert_date_to_timestamps, format_dataframe_timestamps

api_app = Flask(__name__)

# Configure CORS - Allow all origins for development
CORS(api_app, origins=["*"])

# Configure JWT
api_app.config['JWT_SECRET_KEY'] = os.environ.get('DASHBOARD_SECRET_KEY', 'fac8cf149bdd616c07c1a675c4571ccacc40d7f7fe16914cfe0f9f9d966bb773')
api_app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # Token never expires
jwt = JWTManager(api_app)

# User credentials from environment
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
USER_CREDENTIALS = {
    DASHBOARD_USER: DASHBOARD_PASSWORD
}

push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'


# Health check endpoint
@api_app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'service': 'AI Code Review API',
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200


@api_app.route('/')
def home():
    """Serve the frontend index.html"""
    try:
        return send_from_directory('/app/frontend/dist', 'index.html')
    except:
        return """<h2>The code review api server is running.</h2>
                  <p>GitHub project address: <a href="https://github.com/sunmh207/AI-Codereview-Gitlab" target="_blank">
                  https://github.com/sunmh207/AI-Codereview-Gitlab</a></p>
                  <p>Gitee project address: <a href="https://gitee.com/sunminghui/ai-codereview-gitlab" target="_blank">https://gitee.com/sunminghui/ai-codereview-gitlab</a></p>
                  """

@api_app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files from frontend dist directory"""
    try:
        return send_from_directory('/app/frontend/dist', filename)
    except:
        # If file not found, serve index.html for SPA routing
        return send_from_directory('/app/frontend/dist', 'index.html')


@api_app.route('/review/daily_report', methods=['GET'])
def daily_report():
    # 获取当前日期0点和23点59分59秒的时间戳
    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    end_time = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).timestamp()

    try:
        if push_review_enabled:
            df = ReviewService().get_push_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)
        else:
            df = ReviewService().get_mr_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)

        if df.empty:
            logger.info("No data to process.")
            return jsonify({'success': True, 'message': 'No data to process.', 'data': {}}), 200
        # 去重：基于 (author, message) 组合
        df_unique = df.drop_duplicates(subset=["author", "commit_messages"])
        # 按照 author 排序
        df_sorted = df_unique.sort_values(by="author")
        # 转换为适合生成日报的格式
        commits = df_sorted.to_dict(orient="records")
        team_mapping = ReviewService.get_author_team_mapping()

        team_commits = {}
        unassigned_commits = []
        for record in commits:
            author = (record.get('author') or '').strip()
            team_info = team_mapping.get(author)
            webhook_url = team_info.get('webhook_url') if team_info else None
            if team_info and webhook_url:
                team_id = team_info.get('id')
                if team_id not in team_commits:
                    team_commits[team_id] = {
                        'team': team_info,
                        'records': []
                    }
                team_commits[team_id]['records'].append(record)
            else:
                unassigned_commits.append(record)

        reporter = Reporter()
        team_reports_summary = []

        for team_id, payload in team_commits.items():
            team_info = payload['team']
            team_name = team_info.get('name') or '未命名团队'
            try:
                team_report = reporter.generate_report(json.dumps(payload['records'], ensure_ascii=False))
                sent = TeamWebhookNotifier.send_markdown(
                    webhook_url=team_info.get('webhook_url'),
                    title=f"{team_name} 工作日报",
                    content=team_report
                )
                team_reports_summary.append({
                    'team_id': team_id,
                    'team_name': team_name,
                    'member_count': len(payload['records']),
                    'sent': sent,
                    'report': team_report
                })
            except Exception as team_error:
                logger.error("团队[%s]日报生成或推送失败: %s", team_name, team_error)
                team_reports_summary.append({
                    'team_id': team_id,
                    'team_name': team_name,
                    'member_count': len(payload['records']),
                    'sent': False,
                    'error': str(team_error)
                })

        fallback_commits = commits if not team_commits else unassigned_commits
        fallback_report = None
        fallback_sent = False

        if fallback_commits:
            try:
                fallback_report = reporter.generate_report(json.dumps(fallback_commits, ensure_ascii=False))
                notifier.send_notification(
                    content=fallback_report,
                    msg_type="markdown",
                    title="代码提交日报"
                )
                fallback_sent = True
            except Exception as fallback_error:
                logger.error("日报生成或推送失败: %s", fallback_error)

        response_payload = {
            'total_records': len(commits),
            'team_reports': team_reports_summary,
            'unassigned_count': len(unassigned_commits),
            'fallback_sent': fallback_sent
        }
        if fallback_report:
            response_payload['fallback_report'] = fallback_report

        return jsonify({'success': True, 'data': response_payload}), 200
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        return jsonify({'success': False, 'message': f"Failed to generate daily report: {e}"}), 500


# Authentication endpoints
@api_app.route('/api/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'message': 'Username and password are required'}), 400

        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            access_token = create_access_token(identity=username)
            return jsonify({
                'access_token': access_token,
                'username': username,
                'message': 'Login successful'
            }), 200
        else:
            return jsonify({'message': 'Invalid username or password'}), 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'message': 'Login failed'}), 500


@api_app.route('/api/auth/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify JWT token"""
    current_user = get_jwt_identity()
    return jsonify({'username': current_user, 'valid': True}), 200


@api_app.route('/api/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout endpoint"""
    return jsonify({'message': 'Logout successful'}), 200


# Data endpoints
@api_app.route('/api/reviews/mr', methods=['GET'])
@jwt_required()
def get_mr_reviews():
    """Get merge request review data with pagination"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        authors = request.args.getlist('authors')
        project_names = request.args.getlist('project_names')
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        # Sorting parameters
        sort_by = request.args.get('sort_by', 'updated_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Score filtering
        score_min = request.args.get('score_min', type=int)
        score_max = request.args.get('score_max', type=int)

        # Convert dates to timestamps using utility function
        start_timestamp, end_timestamp = convert_date_to_timestamps(start_date, end_date)

        # Get data from service
        df = ReviewService().get_mr_review_logs(
            authors=authors if authors else None,
            project_names=project_names if project_names else None,
            updated_at_gte=start_timestamp,
            updated_at_lte=end_timestamp
        )

        if df.empty:
            return jsonify({'data': [], 'total': 0, 'page': page, 'page_size': page_size}), 200

        # Apply score filtering
        if score_min is not None:
            df = df[df['score'] >= score_min]
        if score_max is not None:
            df = df[df['score'] <= score_max]

        # Apply sorting
        if sort_by in df.columns:
            ascending = sort_order.lower() == 'asc'
            df = df.sort_values(by=sort_by, ascending=ascending)

        # Get total count before pagination
        total = len(df)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        df_page = df.iloc[start_idx:end_idx]

        # Format timestamps using utility function
        df_page = format_dataframe_timestamps(df_page, 'updated_at')

        # Convert to records
        records = df_page.to_dict('records')
        
        return jsonify({
            'data': records, 
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }), 200

    except Exception as e:
        logger.error(f"Get MR reviews error: {e}")
        return jsonify({'message': 'Failed to get MR reviews'}), 500


@api_app.route('/api/reviews/push', methods=['GET'])
@jwt_required()
def get_push_reviews():
    """Get push review data with pagination"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        authors = request.args.getlist('authors')
        project_names = request.args.getlist('project_names')
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        # Sorting parameters
        sort_by = request.args.get('sort_by', 'updated_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Score filtering
        score_min = request.args.get('score_min', type=int)
        score_max = request.args.get('score_max', type=int)

        # Convert dates to timestamps using utility function
        start_timestamp, end_timestamp = convert_date_to_timestamps(start_date, end_date)

        # Get data from service
        df = ReviewService().get_push_review_logs(
            authors=authors if authors else None,
            project_names=project_names if project_names else None,
            updated_at_gte=start_timestamp,
            updated_at_lte=end_timestamp
        )

        if df.empty:
            return jsonify({'data': [], 'total': 0, 'page': page, 'page_size': page_size}), 200

        # Apply score filtering
        if score_min is not None:
            df = df[df['score'] >= score_min]
        if score_max is not None:
            df = df[df['score'] <= score_max]

        # Apply sorting
        if sort_by in df.columns:
            ascending = sort_order.lower() == 'asc'
            df = df.sort_values(by=sort_by, ascending=ascending)

        # Get total count before pagination
        total = len(df)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        df_page = df.iloc[start_idx:end_idx]

        # Format timestamps using utility function
        df_page = format_dataframe_timestamps(df_page, 'updated_at')

        # Convert to records
        records = df_page.to_dict('records')
        
        return jsonify({
            'data': records, 
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }), 200

    except Exception as e:
        logger.error(f"Get push reviews error: {e}")
        return jsonify({'message': 'Failed to get push reviews'}), 500


@api_app.route('/api/statistics/projects', methods=['GET'])
@jwt_required()
def get_project_statistics():
    """Get project statistics"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        review_type = request.args.get('type', 'mr')  # 'mr' or 'push'

        # Convert dates to timestamps using utility function
        start_timestamp, end_timestamp = convert_date_to_timestamps(start_date, end_date)

        # Get data from service
        if review_type == 'push':
            df = ReviewService().get_push_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )
        else:
            df = ReviewService().get_mr_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )

        if df.empty:
            return jsonify({'project_counts': [], 'project_scores': []}), 200

        # Calculate project statistics
        project_counts = df['project_name'].value_counts().reset_index()
        project_counts.columns = ['project_name', 'count']

        project_scores = df.groupby('project_name')['score'].mean().reset_index()
        project_scores.columns = ['project_name', 'average_score']

        return jsonify({
            'project_counts': project_counts.to_dict('records'),
            'project_scores': project_scores.to_dict('records')
        }), 200

    except Exception as e:
        logger.error(f"Get project statistics error: {e}")
        return jsonify({'message': 'Failed to get project statistics'}), 500


@api_app.route('/api/statistics/authors', methods=['GET'])
@jwt_required()
def get_author_statistics():
    """Get author statistics"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        review_type = request.args.get('type', 'mr')  # 'mr' or 'push'

        # Convert dates to timestamps using utility function
        start_timestamp, end_timestamp = convert_date_to_timestamps(start_date, end_date)

        # Get data from service
        if review_type == 'push':
            df = ReviewService().get_push_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )
        else:
            df = ReviewService().get_mr_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )

        if df.empty:
            return jsonify({
                'author_counts': [],
                'author_scores': [],
                'author_code_lines': []
            }), 200

        # Calculate author statistics
        author_counts = df['author'].value_counts().reset_index()
        author_counts.columns = ['author', 'count']

        author_scores = df.groupby('author')['score'].mean().reset_index()
        author_scores.columns = ['author', 'average_score']

        # Calculate code lines statistics
        author_code_lines = df.groupby('author').agg({
            'additions': 'sum',
            'deletions': 'sum'
        }).reset_index()

        return jsonify({
            'author_counts': author_counts.to_dict('records'),
            'author_scores': author_scores.to_dict('records'),
            'author_code_lines': author_code_lines.to_dict('records')
        }), 200

    except Exception as e:
        logger.error(f"Get author statistics error: {e}")
        return jsonify({'message': 'Failed to get author statistics'}), 500


@api_app.route('/api/statistics/<stat_type>', methods=['GET'])
@jwt_required()
def get_statistics(stat_type):
    """Get specific statistics by type"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        review_type = request.args.get('type', 'mr')  # 'mr' or 'push'

        # Convert dates to timestamps using utility function
        start_timestamp, end_timestamp = convert_date_to_timestamps(start_date, end_date)

        # Get data from service
        if review_type == 'push':
            df = ReviewService().get_push_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )
        else:
            df = ReviewService().get_mr_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )

        if df.empty:
            return jsonify({'data': []}), 200

        # Calculate statistics based on type
        if stat_type == 'project_counts':
            result = df['project_name'].value_counts().reset_index()
            result.columns = ['project_name', 'count']
        elif stat_type == 'project_scores':
            result = df.groupby('project_name')['score'].mean().reset_index()
            result.columns = ['project_name', 'average_score']
        elif stat_type == 'author_counts':
            result = df['author'].value_counts().reset_index()
            result.columns = ['author', 'count']
        elif stat_type == 'author_scores':
            result = df.groupby('author')['score'].mean().reset_index()
            result.columns = ['author', 'average_score']
        elif stat_type == 'author_code_lines':
            result = df.groupby('author').agg({
                'additions': 'sum',
                'deletions': 'sum'
            }).reset_index()
        else:
            return jsonify({'message': 'Invalid statistics type'}), 400

        return jsonify({'data': result.to_dict('records')}), 200

    except Exception as e:
        logger.error(f"Get statistics error: {e}")
        return jsonify({'message': 'Failed to get statistics'}), 500

        # Calculate code lines if available
        author_code_lines = []
        if 'additions' in df.columns and 'deletions' in df.columns:
            author_additions = df.groupby('author')['additions'].sum().reset_index()
            author_deletions = df.groupby('author')['deletions'].sum().reset_index()
            author_code_lines = []
            for _, row in author_additions.iterrows():
                author = row['author']
                additions = row['additions']
                deletions = author_deletions[author_deletions['author'] == author]['deletions'].iloc[0] if not author_deletions[author_deletions['author'] == author].empty else 0
                author_code_lines.append({
                    'author': author,
                    'additions': additions,
                    'deletions': deletions
                })

        return jsonify({
            'author_counts': author_counts.to_dict('records'),
            'author_scores': author_scores.to_dict('records'),
            'author_code_lines': author_code_lines
        }), 200

    except Exception as e:
        logger.error(f"Get author statistics error: {e}")
        return jsonify({'message': 'Failed to get author statistics'}), 500


@api_app.route('/api/metadata', methods=['GET'])
@jwt_required()
def get_metadata():
    """Get metadata for filters"""
    try:
        # Get query parameters for date range
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        review_type = request.args.get('type', 'mr')  # 'mr' or 'push'

        # Convert dates to timestamps using utility function
        start_timestamp, end_timestamp = convert_date_to_timestamps(start_date, end_date)

        # Get data from service
        if review_type == 'push':
            df = ReviewService().get_push_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )
        else:
            df = ReviewService().get_mr_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )

        if df.empty:
            return jsonify({
                'authors': [],
                'project_names': [],
                'push_review_enabled': push_review_enabled
            }), 200

        # Get unique values
        authors = sorted(df["author"].dropna().unique().tolist())
        project_names = sorted(df["project_name"].dropna().unique().tolist())

        return jsonify({
            'authors': authors,
            'project_names': project_names,
            'push_review_enabled': push_review_enabled
        }), 200

    except Exception as e:
        logger.error(f"Get metadata error: {e}")
        return jsonify({'message': 'Failed to get metadata'}), 500


@api_app.route('/api/project-webhook-config', methods=['GET'])
@jwt_required()
def get_project_webhook_configs():
    """获取项目webhook配置列表"""
    try:
        project_name = request.args.get('project_name')
        project_name = project_name.strip() if project_name else None
        url_slug = request.args.get('url_slug')
        url_slug = url_slug.strip() if url_slug else None

        configs = ReviewService.get_project_webhook_config(project_name=project_name, url_slug=url_slug)

        return jsonify({
            'success': True,
            'data': configs
        }), 200
    except Exception as e:
        logger.error(f"Get project webhook configs error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get project webhook configs'}), 500


@api_app.route('/api/project-webhook-config', methods=['POST'])
@jwt_required()
def create_or_update_project_webhook_config():
    """创建或更新项目webhook配置"""
    try:
        data = request.get_json()

        # 验证必填字段
        project_name = (data.get('project_name') or '').strip()
        if not project_name:
            return jsonify({'success': False, 'message': 'Project name is required'}), 400

        url_slug = (data.get('url_slug') or '').strip() or None

        # 转换enabled字段为整数
        for field in ['dingtalk_enabled', 'wecom_enabled', 'feishu_enabled', 'extra_webhook_enabled']:
            if field in data:
                data[field] = int(data[field]) if data[field] is not None else 0

        ReviewService.upsert_project_webhook_config(
            project_name=project_name,
            url_slug=url_slug,
            dingtalk_webhook_url=data.get('dingtalk_webhook_url'),
            wecom_webhook_url=data.get('wecom_webhook_url'),
            feishu_webhook_url=data.get('feishu_webhook_url'),
            extra_webhook_url=data.get('extra_webhook_url'),
            dingtalk_enabled=data.get('dingtalk_enabled', 0),
            wecom_enabled=data.get('wecom_enabled', 0),
            feishu_enabled=data.get('feishu_enabled', 0),
            extra_webhook_enabled=data.get('extra_webhook_enabled', 0)
        )

        return jsonify({'success': True, 'message': 'Project webhook config saved successfully'}), 200
    except ValueError as e:
        logger.warning(f"Save project webhook config validation error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Save project webhook config error: {e}")
        return jsonify({'success': False, 'message': 'Failed to save project webhook config'}), 500


@api_app.route('/api/project-webhook-config/<project_name>', methods=['DELETE'])
@jwt_required()
def delete_project_webhook_config(project_name):
    """删除项目webhook配置"""
    try:
        normalized_project_name = (project_name or '').strip()
        if not normalized_project_name:
            return jsonify({'success': False, 'message': 'Project name is required'}), 400

        success = ReviewService.delete_project_webhook_config(normalized_project_name)

        if success:
            return jsonify({'success': True, 'message': 'Project webhook config deleted successfully'}), 200
        else:
            return jsonify({'success': False, 'message': 'Project webhook config not found'}), 404
    except Exception as e:
        logger.error(f"Delete project webhook config error: {e}")
        return jsonify({'success': False, 'message': 'Failed to delete project webhook config'}), 500


@api_app.route('/api/projects', methods=['GET'])
@jwt_required()
def get_projects_overview():
    """获取项目管理概览列表（支持分页）"""
    try:
        search = request.args.get('search')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        # 获取所有项目
        all_projects = ReviewService.get_project_overview(search=search)
        total = len(all_projects)
        
        # 分页
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        projects = all_projects[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'data': projects,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }), 200
    except Exception as e:
        logger.error(f"Get projects overview error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get projects overview'}), 500


@api_app.route('/api/projects/gitlab-projects', methods=['POST'])
@jwt_required()
def get_gitlab_projects():
    """从 GitLab 获取项目列表"""
    try:
        from biz.gitlab.gitlab_service import GitLabService
        
        data = request.get_json() or {}
        source_type = data.get('source_type', 'user')
        group_id = data.get('group_id')
        gitlab_url = data.get('gitlab_url')
        gitlab_token = data.get('gitlab_token')
        
        # 初始化 GitLab 服务
        gitlab_service = GitLabService(gitlab_url=gitlab_url, gitlab_token=gitlab_token)
        
        # 根据来源类型获取项目
        if source_type == 'group':
            if not group_id or not group_id.strip():
                return jsonify({'success': False, 'message': 'Group ID 不能为空'}), 400
            projects = gitlab_service.get_group_projects(group_id.strip())
        else:  # user
            projects = gitlab_service.get_user_projects(membership=True)
        
        if projects is None:
            return jsonify({'success': False, 'message': '无法从 GitLab 获取项目列表，请检查配置和权限'}), 400
        
        logger.info(f"从 GitLab 获取到 {len(projects)} 个项目")
        return jsonify({'success': True, 'data': projects}), 200
    except Exception as e:
        logger.error(f"Get GitLab projects error: {e}")
        return jsonify({'success': False, 'message': f'获取项目列表失败: {str(e)}'}), 500


@api_app.route('/api/projects/import-from-gitlab', methods=['POST'])
@jwt_required()
def import_projects_from_gitlab():
    """从 GitLab 批量导入项目配置"""
    try:
        data = request.get_json() or {}
        projects = data.get('projects', [])
        
        if not isinstance(projects, list) or len(projects) == 0:
            return jsonify({'success': False, 'message': '请选择要导入的项目'}), 400
        
        imported_count = 0
        errors = []
        
        for project in projects:
            project_name = project.get('name')
            path_with_namespace = project.get('path_with_namespace')
            
            if not project_name:
                continue
            
            try:
                # 创建或更新项目 webhook 配置
                ReviewService.upsert_project_webhook_config(
                    project_name=project_name,
                    url_slug=path_with_namespace,
                    dingtalk_webhook_url=None,
                    wecom_webhook_url=None,
                    feishu_webhook_url=None,
                    extra_webhook_url=None,
                    dingtalk_enabled=0,
                    wecom_enabled=0,
                    feishu_enabled=0,
                    extra_webhook_enabled=0
                )
                imported_count += 1
            except Exception as e:
                errors.append(f"{project_name}: {str(e)}")
                logger.error(f"Failed to import project {project_name}: {e}")
        
        message = f'成功导入 {imported_count} 个项目'
        if errors:
            message += f'，{len(errors)} 个失败'
        
        logger.info(f"项目导入完成：{message}")
        return jsonify({
            'success': True,
            'data': {
                'imported': imported_count,
                'total': len(projects),
                'errors': errors
            },
            'message': message
        }), 200
    except Exception as e:
        logger.error(f"Import projects from GitLab error: {e}")
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500


@api_app.route('/api/projects/<project_name>/summary', methods=['GET'])
@jwt_required()
def get_project_summary(project_name):
    """获取指定项目的审查与 webhook 概览"""
    try:
        normalized_project_name = (project_name or '').strip()
        if not normalized_project_name:
            return jsonify({'success': False, 'message': 'Project name is required'}), 400

        summary = ReviewService.get_project_summary(normalized_project_name)
        if summary is None:
            return jsonify({'success': False, 'message': 'Project not found'}), 404
        return jsonify({'success': True, 'data': summary}), 200
    except ValueError as e:
        logger.warning(f"Get project summary validation error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Get project summary error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get project summary'}), 500


@api_app.route('/api/teams', methods=['GET'])
@jwt_required()
def get_teams():
    """获取团队列表"""
    try:
        include_members = request.args.get('include_members', '1') != '0'
        teams = ReviewService.list_teams(include_members=include_members)
        return jsonify({'success': True, 'data': teams}), 200
    except Exception as e:
        logger.error(f"Get teams error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get teams'}), 500


@api_app.route('/api/teams/<int:team_id>', methods=['GET'])
@jwt_required()
def get_team_detail(team_id: int):
    """获取团队详情"""
    try:
        include_members = request.args.get('include_members', '1') != '0'
        team = ReviewService.get_team(team_id, include_members=include_members)
        if not team:
            return jsonify({'success': False, 'message': 'Team not found'}), 404
        return jsonify({'success': True, 'data': team}), 200
    except Exception as e:
        logger.error(f"Get team detail error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get team detail'}), 500


@api_app.route('/api/teams', methods=['POST'])
@jwt_required()
def create_team():
    """创建团队"""
    try:
        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'message': '团队名称不能为空'}), 400

        team = ReviewService.create_team(
            name=name,
            webhook_url=data.get('webhook_url'),
            description=data.get('description')
        )
        if not team:
            return jsonify({'success': False, 'message': '团队创建失败'}), 500
        return jsonify({'success': True, 'data': team}), 201
    except ValueError as e:
        logger.warning(f"Create team validation error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Create team error: {e}")
        return jsonify({'success': False, 'message': 'Failed to create team'}), 500


@api_app.route('/api/teams/<int:team_id>', methods=['PUT'])
@jwt_required()
def update_team(team_id: int):
    """更新团队信息"""
    try:
        data = request.get_json() or {}
        team = ReviewService.update_team(
            team_id=team_id,
            name=data.get('name'),
            webhook_url=data.get('webhook_url'),
            description=data.get('description')
        )
        if not team:
            return jsonify({'success': False, 'message': 'Team not found'}), 404
        return jsonify({'success': True, 'data': team}), 200
    except ValueError as e:
        logger.warning(f"Update team validation error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Update team error: {e}")
        return jsonify({'success': False, 'message': 'Failed to update team'}), 500


@api_app.route('/api/teams/<int:team_id>', methods=['DELETE'])
@jwt_required()
def delete_team(team_id: int):
    """删除团队"""
    try:
        deleted = ReviewService.delete_team(team_id)
        if not deleted:
            return jsonify({'success': False, 'message': 'Team not found'}), 404
        return jsonify({'success': True, 'message': 'Team deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Delete team error: {e}")
        return jsonify({'success': False, 'message': 'Failed to delete team'}), 500


@api_app.route('/api/teams/<int:team_id>/members', methods=['POST'])
@jwt_required()
def add_team_members(team_id: int):
    """批量添加团队成员"""
    try:
        data = request.get_json() or {}
        authors = data.get('authors')
        if not isinstance(authors, list):
            return jsonify({'success': False, 'message': 'authors 字段必须为数组'}), 400
        added = ReviewService.add_team_members(team_id, authors)
        team = ReviewService.get_team(team_id, include_members=True)
        if not team:
            return jsonify({'success': False, 'message': 'Team not found'}), 404
        return jsonify({'success': True, 'data': {'added': added, 'team': team}}), 200
    except ValueError as e:
        logger.warning(f"Add team members validation error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Add team members error: {e}")
        return jsonify({'success': False, 'message': 'Failed to add team members'}), 500


@api_app.route('/api/teams/<int:team_id>/members/<author>', methods=['DELETE'])
@jwt_required()
def remove_team_member(team_id: int, author: str):
    """移除团队成员"""
    try:
        removed = ReviewService.remove_team_member(team_id, author)
        if not removed:
            return jsonify({'success': False, 'message': '成员不存在或团队不存在'}), 404
        team = ReviewService.get_team(team_id, include_members=True)
        return jsonify({'success': True, 'data': team}), 200
    except ValueError as e:
        logger.warning(f"Remove team member validation error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Remove team member error: {e}")
        return jsonify({'success': False, 'message': 'Failed to remove team member'}), 500


@api_app.route('/api/teams/<int:team_id>/sync-from-gitlab', methods=['POST'])
@jwt_required()
def sync_team_from_gitlab(team_id: int):
    """从 GitLab 同步团队成员"""
    try:
        data = request.get_json() or {}
        source_type = data.get('source_type', 'project')
        source_id = (data.get('source_id') or '').strip()
        gitlab_url = data.get('gitlab_url')
        gitlab_token = data.get('gitlab_token')
        merge_strategy = data.get('merge_strategy', 'replace')

        # 验证必填参数
        if not source_id:
            return jsonify({'success': False, 'message': 'GitLab 项目/组织 ID 不能为空'}), 400

        if source_type not in ['project', 'group']:
            return jsonify({'success': False, 'message': "来源类型必须是 'project' 或 'group'"}), 400

        if merge_strategy not in ['replace', 'merge']:
            return jsonify({'success': False, 'message': "合并策略必须是 'replace' 或 'merge'"}), 400

        # 执行同步
        result = ReviewService.sync_team_from_gitlab(
            team_id=team_id,
            source_type=source_type,
            source_id=source_id,
            gitlab_url=gitlab_url,
            gitlab_token=gitlab_token,
            merge_strategy=merge_strategy
        )

        logger.info(f"团队 {team_id} 从 GitLab 同步成功：新增 {result['added']} 人，移除 {result['removed']} 人")
        return jsonify({
            'success': True,
            'data': result,
            'message': f"同步成功：新增 {result['added']} 人，移除 {result['removed']} 人，当前共 {result['total']} 人"
        }), 200
    except ValueError as e:
        logger.warning(f"Sync team from GitLab validation error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Sync team from GitLab error: {e}")
        return jsonify({'success': False, 'message': f'同步失败: {str(e)}'}), 500


def setup_scheduler():
    """
    配置并启动定时任务调度器
    """
    try:
        scheduler = BackgroundScheduler()
        crontab_expression = os.getenv('REPORT_CRONTAB_EXPRESSION', '0 18 * * 1-5')
        cron_parts = crontab_expression.split()
        cron_minute, cron_hour, cron_day, cron_month, cron_day_of_week = cron_parts

        # Schedule the task based on the crontab expression
        scheduler.add_job(
            daily_report,
            trigger=CronTrigger(
                minute=cron_minute,
                hour=cron_hour,
                day=cron_day,
                month=cron_month,
                day_of_week=cron_day_of_week
            )
        )

        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started successfully.")

        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())
    except Exception as e:
        logger.error(f"Error setting up scheduler: {e}")
        logger.error(traceback.format_exc())


# 处理 GitLab Merge Request Webhook
@api_app.route('/review/webhook', methods=['POST'])
def handle_webhook():
    # 获取请求的JSON数据
    if request.is_json:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        # 判断是GitLab还是GitHub的webhook
        webhook_source = request.headers.get('X-GitHub-Event')

        if webhook_source:  # GitHub webhook
            return handle_github_webhook(webhook_source, data)
        else:  # GitLab webhook
            return handle_gitlab_webhook(data)
    else:
        return jsonify({'message': 'Invalid data format'}), 400


def handle_github_webhook(event_type, data):
    # 获取GitHub配置
    github_token = os.getenv('GITHUB_ACCESS_TOKEN') or request.headers.get('X-GitHub-Token')
    if not github_token:
        return jsonify({'message': 'Missing GitHub access token'}), 400

    github_url = os.getenv('GITHUB_URL') or 'https://github.com'
    github_url_slug = slugify_url(github_url)

    # 打印整个payload数据
    logger.info(f'Received GitHub event: {event_type}')
    logger.info(f'Payload: {json.dumps(data)}')

    if event_type == "pull_request":
        # 使用handle_queue进行异步处理
        handle_queue(handle_github_pull_request_event, data, github_token, github_url, github_url_slug)
        # 立马返回响应
        return jsonify(
            {'message': f'GitHub request received(event_type={event_type}), will process asynchronously.'}), 200
    elif event_type == "push":
        # 使用handle_queue进行异步处理
        handle_queue(handle_github_push_event, data, github_token, github_url, github_url_slug)
        # 立马返回响应
        return jsonify(
            {'message': f'GitHub request received(event_type={event_type}), will process asynchronously.'}), 200
    else:
        error_message = f'Only pull_request and push events are supported for GitHub webhook, but received: {event_type}.'
        logger.error(error_message)
        return jsonify(error_message), 400


def handle_gitlab_webhook(data):
    object_kind = data.get("object_kind")

    # 优先从请求头获取，如果没有，则从环境变量获取，如果没有，则从推送事件中获取
    gitlab_url = os.getenv('GITLAB_URL') or request.headers.get('X-Gitlab-Instance')
    if not gitlab_url:
        repository = data.get('repository')
        if not repository:
            return jsonify({'message': 'Missing GitLab URL'}), 400
        homepage = repository.get("homepage")
        if not homepage:
            return jsonify({'message': 'Missing GitLab URL'}), 400
        try:
            parsed_url = urlparse(homepage)
            gitlab_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        except Exception as e:
            return jsonify({"error": f"Failed to parse homepage URL: {str(e)}"}), 400

    # 优先从环境变量获取，如果没有，则从请求头获取
    gitlab_token = os.getenv('GITLAB_ACCESS_TOKEN') or request.headers.get('X-Gitlab-Token')
    # 如果gitlab_token为空，返回错误
    if not gitlab_token:
        return jsonify({'message': 'Missing GitLab access token'}), 400

    gitlab_url_slug = slugify_url(gitlab_url)

    # 打印整个payload数据，或根据需求进行处理
    logger.info(f'Received event: {object_kind}')
    logger.info(f'Payload: {json.dumps(data)}')

    # 处理Merge Request Hook
    if object_kind == "merge_request":
        # 创建一个新进程进行异步处理
        handle_queue(handle_merge_request_event, data, gitlab_token, gitlab_url, gitlab_url_slug)
        # 立马返回响应
        return jsonify(
            {'message': f'Request received(object_kind={object_kind}), will process asynchronously.'}), 200
    elif object_kind == "push":
        # 创建一个新进程进行异步处理
        # TODO check if PUSH_REVIEW_ENABLED is needed here
        handle_queue(handle_push_event, data, gitlab_token, gitlab_url, gitlab_url_slug)
        # 立马返回响应
        return jsonify(
            {'message': f'Request received(object_kind={object_kind}), will process asynchronously.'}), 200
    else:
        error_message = f'Only merge_request and push events are supported (both Webhook and System Hook), but received: {object_kind}.'
        logger.error(error_message)
        return jsonify(error_message), 400


if __name__ == '__main__':
    check_config()
    # 启动定时任务调度器
    setup_scheduler()

    # 启动Flask API服务
    port = int(os.environ.get('SERVER_PORT', 5001))
    api_app.run(host='0.0.0.0', port=port)
