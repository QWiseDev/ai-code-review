import sqlite3
from typing import Dict, List, Optional

import pandas as pd

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity


class ReviewService:
    DB_FILE = "data/data.db"

    @staticmethod
    def init_db():
        """初始化数据库及表结构"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                cursor.execute('''
                        CREATE TABLE IF NOT EXISTS mr_review_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            project_name TEXT,
                            author TEXT,
                            source_branch TEXT,
                            target_branch TEXT,
                            updated_at INTEGER,
                            commit_messages TEXT,
                            score INTEGER,
                            url TEXT,
                            review_result TEXT,
                            additions INTEGER DEFAULT 0,
                            deletions INTEGER DEFAULT 0,
                            last_commit_id TEXT DEFAULT ''
                        )
                    ''')
                cursor.execute('''
                        CREATE TABLE IF NOT EXISTS push_review_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            project_name TEXT,
                            author TEXT,
                            branch TEXT,
                            updated_at INTEGER,
                            commit_messages TEXT,
                            score INTEGER,
                            review_result TEXT,
                            additions INTEGER DEFAULT 0,
                            deletions INTEGER DEFAULT 0
                        )
                    ''')
                # 确保旧版本的mr_review_log、push_review_log表添加additions、deletions列
                tables = ["mr_review_log", "push_review_log"]
                columns = ["additions", "deletions"]
                for table in tables:
                    cursor.execute(f"PRAGMA table_info({table})")
                    current_columns = [col[1] for col in cursor.fetchall()]
                    for column in columns:
                        if column not in current_columns:
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER DEFAULT 0")

                # 为旧版本的mr_review_log表添加last_commit_id字段
                mr_columns = [
                    {
                        "name": "last_commit_id",
                        "type": "TEXT",
                        "default": "''"
                    }
                ]
                cursor.execute(f"PRAGMA table_info('mr_review_log')")
                current_columns = [col[1] for col in cursor.fetchall()]
                for column in mr_columns:
                    if column.get("name") not in current_columns:
                        cursor.execute(f"ALTER TABLE mr_review_log ADD COLUMN {column.get('name')} {column.get('type')} "
                                       f"DEFAULT {column.get('default')}")

                conn.commit()
                # 添加时间字段索引（默认查询就需要时间范围）
                conn.execute('CREATE INDEX IF NOT EXISTS idx_push_review_log_updated_at ON '
                             'push_review_log (updated_at);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_mr_review_log_updated_at ON mr_review_log (updated_at);')

                # 创建项目webhook配置表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS project_webhook_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_name TEXT UNIQUE NOT NULL,
                        url_slug TEXT,
                        dingtalk_webhook_url TEXT,
                        wecom_webhook_url TEXT,
                        feishu_webhook_url TEXT,
                        extra_webhook_url TEXT,
                        dingtalk_enabled INTEGER DEFAULT 0,
                        wecom_enabled INTEGER DEFAULT 0,
                        feishu_enabled INTEGER DEFAULT 0,
                        extra_webhook_enabled INTEGER DEFAULT 0,
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        updated_at INTEGER DEFAULT (strftime('%s', 'now'))
                    )
                ''')

                # 创建索引
                conn.execute('CREATE INDEX IF NOT EXISTS idx_project_webhook_config_project_name ON project_webhook_config (project_name);')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_project_webhook_config_url_slug ON project_webhook_config (url_slug);')

                # 创建团队及成员关系表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS teams (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        webhook_url TEXT,
                        description TEXT,
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        updated_at INTEGER DEFAULT (strftime('%s', 'now'))
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS team_members (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        team_id INTEGER NOT NULL,
                        author TEXT NOT NULL UNIQUE,
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        FOREIGN KEY(team_id) REFERENCES teams(id) ON DELETE CASCADE
                    )
                ''')

                conn.execute('CREATE INDEX IF NOT EXISTS idx_teams_name ON teams (name);')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members (team_id);')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_team_members_author ON team_members (author);')
        except sqlite3.DatabaseError as e:
            print(f"Database initialization failed: {e}")

    @staticmethod
    def insert_mr_review_log(entity: MergeRequestReviewEntity):
        """插入合并请求审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                                INSERT INTO mr_review_log (project_name,author, source_branch, target_branch, 
                                updated_at, commit_messages, score, url,review_result, additions, deletions, 
                                last_commit_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''',
                               (entity.project_name, entity.author, entity.source_branch,
                                entity.target_branch, entity.updated_at, entity.commit_messages, entity.score,
                                entity.url, entity.review_result, entity.additions, entity.deletions,
                                entity.last_commit_id))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting review log: {e}")

    @staticmethod
    def get_mr_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                           updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的合并请求审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                query = """
                            SELECT project_name, author, source_branch, target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions
                            FROM mr_review_log
                            WHERE 1=1
                            """
                params = []

                if authors:
                    placeholders = ','.join(['?'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['?'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                if updated_at_gte is not None:
                    query += " AND updated_at >= ?"
                    params.append(updated_at_gte)

                if updated_at_lte is not None:
                    query += " AND updated_at <= ?"
                    params.append(updated_at_lte)
                query += " ORDER BY updated_at DESC"
                df = pd.read_sql_query(sql=query, con=conn, params=params)
            return df
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving review logs: {e}")
            return pd.DataFrame()

    @staticmethod
    def check_mr_last_commit_id_exists(project_name: str, source_branch: str, target_branch: str, last_commit_id: str) -> bool:
        """检查指定项目的Merge Request是否已经存在相同的last_commit_id"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM mr_review_log 
                    WHERE project_name = ? AND source_branch = ? AND target_branch = ? AND last_commit_id = ?
                ''', (project_name, source_branch, target_branch, last_commit_id))
                count = cursor.fetchone()[0]
                return count > 0
        except sqlite3.DatabaseError as e:
            print(f"Error checking last_commit_id: {e}")
            return False

    @staticmethod
    def insert_push_review_log(entity: PushReviewEntity):
        """插入推送审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                                INSERT INTO push_review_log (project_name,author, branch, updated_at, commit_messages, score,review_result, additions, deletions)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''',
                               (entity.project_name, entity.author, entity.branch,
                                entity.updated_at, entity.commit_messages, entity.score,
                                entity.review_result, entity.additions, entity.deletions))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting review log: {e}")

    @staticmethod
    def get_push_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                             updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的推送审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                # 基础查询
                query = """
                    SELECT project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions
                    FROM push_review_log
                    WHERE 1=1
                """
                params = []

                # 动态添加 authors 条件
                if authors:
                    placeholders = ','.join(['?'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['?'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                # 动态添加 updated_at_gte 条件
                if updated_at_gte is not None:
                    query += " AND updated_at >= ?"
                    params.append(updated_at_gte)

                # 动态添加 updated_at_lte 条件
                if updated_at_lte is not None:
                    query += " AND updated_at <= ?"
                    params.append(updated_at_lte)

                # 按 updated_at 降序排序
                query += " ORDER BY updated_at DESC"

                # 执行查询
                df = pd.read_sql_query(sql=query, con=conn, params=params)
                return df
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving push review logs: {e}")
            return pd.DataFrame()

    @staticmethod
    def upsert_project_webhook_config(project_name: str, url_slug: str = None, dingtalk_webhook_url: str = None,
                                     wecom_webhook_url: str = None, feishu_webhook_url: str = None,
                                     extra_webhook_url: str = None, dingtalk_enabled: int = 0,
                                     wecom_enabled: int = 0, feishu_enabled: int = 0,
                                     extra_webhook_enabled: int = 0):
        """插入或更新项目webhook配置"""
        try:
            normalized_project_name = (project_name or '').strip()
            if not normalized_project_name:
                raise ValueError("Project name must not be empty.")

            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO project_webhook_config (
                        project_name,
                        url_slug,
                        dingtalk_webhook_url,
                        wecom_webhook_url,
                        feishu_webhook_url,
                        extra_webhook_url,
                        dingtalk_enabled,
                        wecom_enabled,
                        feishu_enabled,
                        extra_webhook_enabled
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_name) DO UPDATE SET
                        url_slug=excluded.url_slug,
                        dingtalk_webhook_url=excluded.dingtalk_webhook_url,
                        wecom_webhook_url=excluded.wecom_webhook_url,
                        feishu_webhook_url=excluded.feishu_webhook_url,
                        extra_webhook_url=excluded.extra_webhook_url,
                        dingtalk_enabled=excluded.dingtalk_enabled,
                        wecom_enabled=excluded.wecom_enabled,
                        feishu_enabled=excluded.feishu_enabled,
                        extra_webhook_enabled=excluded.extra_webhook_enabled,
                        updated_at=strftime('%s', 'now')
                ''', (
                    normalized_project_name,
                    url_slug.strip() if url_slug else None,
                    (dingtalk_webhook_url or '').strip() or None,
                    (wecom_webhook_url or '').strip() or None,
                    (feishu_webhook_url or '').strip() or None,
                    (extra_webhook_url or '').strip() or None,
                    int(bool(dingtalk_enabled)),
                    int(bool(wecom_enabled)),
                    int(bool(feishu_enabled)),
                    int(bool(extra_webhook_enabled))
                ))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error upserting project webhook config: {e}")

    @staticmethod
    def get_project_webhook_config(project_name: str = None, url_slug: str = None):
        """获取项目webhook配置"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                if project_name:
                    cursor.execute('''
                        SELECT * FROM project_webhook_config WHERE project_name = ?
                    ''', (project_name,))
                elif url_slug:
                    cursor.execute('''
                        SELECT * FROM project_webhook_config WHERE url_slug = ?
                    ''', (url_slug,))
                else:
                    cursor.execute('''
                        SELECT * FROM project_webhook_config ORDER BY project_name
                    ''')

                columns = [description[0] for description in cursor.description]
                results = cursor.fetchall()

                if project_name or url_slug:
                    return ReviewService._format_project_webhook_record(columns, results[0]) if results else None
                else:
                    return [ReviewService._format_project_webhook_record(columns, row) for row in results]
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving project webhook config: {e}")
            return None if project_name or url_slug else []

    @staticmethod
    def _format_project_webhook_record(columns, row):
        """格式化项目 webhook 配置记录"""
        record = dict(zip(columns, row))
        for field in ['dingtalk_enabled', 'wecom_enabled', 'feishu_enabled', 'extra_webhook_enabled']:
            if field in record and record[field] is not None:
                record[field] = int(record[field])
            else:
                record[field] = 0
        return record

    @staticmethod
    def get_effective_project_webhook_config(project_name: str = None, url_slug: str = None):
        """
        获取项目 webhook 配置，优先按项目名称匹配，若未命中则尝试 url_slug。
        """
        config = None
        if project_name:
            config = ReviewService.get_project_webhook_config(project_name=project_name)
        if not config and url_slug:
            config = ReviewService.get_project_webhook_config(url_slug=url_slug)
        return config

    @staticmethod
    def _build_enabled_channels(config: dict = None):
        """根据配置生成已启用的通知渠道列表"""
        if not config:
            return []
        channel_map = {
            'dingtalk_enabled': 'dingtalk',
            'wecom_enabled': 'wecom',
            'feishu_enabled': 'feishu',
            'extra_webhook_enabled': 'extra'
        }
        enabled_channels = []
        for field, channel in channel_map.items():
            if int(config.get(field, 0) or 0) == 1:
                enabled_channels.append(channel)
        return enabled_channels

    @staticmethod
    def get_project_overview(search: str = None):
        """获取项目汇总列表"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()

                # MR 审查统计
                cursor.execute('''
                    SELECT project_name, COUNT(*) AS count, MAX(updated_at) AS last_updated
                    FROM mr_review_log
                    WHERE project_name IS NOT NULL AND TRIM(project_name) != ''
                    GROUP BY project_name
                ''')
                mr_stats = {
                    row[0]: {
                        'mr_review_count': int(row[1] or 0),
                        'mr_last_review_at': int(row[2] or 0) if row[2] else None
                    }
                    for row in cursor.fetchall()
                }

                # Push 审查统计
                cursor.execute('''
                    SELECT project_name, COUNT(*) AS count, MAX(updated_at) AS last_updated
                    FROM push_review_log
                    WHERE project_name IS NOT NULL AND TRIM(project_name) != ''
                    GROUP BY project_name
                ''')
                push_stats = {
                    row[0]: {
                        'push_review_count': int(row[1] or 0),
                        'push_last_review_at': int(row[2] or 0) if row[2] else None
                    }
                    for row in cursor.fetchall()
                }

                # Webhook 配置
                cursor.execute('SELECT * FROM project_webhook_config')
                webhook_columns = [desc[0] for desc in cursor.description] if cursor.description else []
                webhook_configs = {}
                if webhook_columns:
                    for row in cursor.fetchall():
                        record = ReviewService._format_project_webhook_record(webhook_columns, row)
                        webhook_configs[record.get('project_name')] = record
                else:
                    cursor.fetchall()  # 清空游标

            # 合并项目列表
            project_names = set(mr_stats.keys()) | set(push_stats.keys()) | set(webhook_configs.keys())
            overview = []
            for name in project_names:
                if not name:
                    continue
                mr_info = mr_stats.get(name, {})
                push_info = push_stats.get(name, {})
                webhook_config = webhook_configs.get(name)

                mr_count = int(mr_info.get('mr_review_count', 0) or 0)
                push_count = int(push_info.get('push_review_count', 0) or 0)
                mr_last = mr_info.get('mr_last_review_at')
                push_last = push_info.get('push_last_review_at')
                last_review_at = max(filter(None, [mr_last, push_last])) if (mr_last or push_last) else None

                record = {
                    'project_name': name,
                    'mr_review_count': mr_count,
                    'push_review_count': push_count,
                    'total_review_count': mr_count + push_count,
                    'last_review_at': last_review_at,
                    'webhook_config': webhook_config,
                    'webhook_enabled_channels': ReviewService._build_enabled_channels(webhook_config)
                }
                overview.append(record)

            if search:
                keyword = search.strip().lower()
                overview = [
                    item for item in overview
                    if keyword in item['project_name'].lower()
                    or (item['webhook_config'] and keyword in (item['webhook_config'].get('url_slug') or '').lower())
                ]

            overview.sort(key=lambda item: (item['last_review_at'] or 0, item['project_name']), reverse=True)
            return overview
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving project overview: {e}")
            return []

    @staticmethod
    def get_project_summary(project_name: str):
        """获取指定项目的审查统计与 webhook 概览"""
        normalized_name = (project_name or '').strip()
        if not normalized_name:
            raise ValueError("Project name must not be empty.")

        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT COUNT(*), MAX(updated_at)
                    FROM mr_review_log
                    WHERE project_name = ?
                ''', (normalized_name,))
                mr_count, mr_last = cursor.fetchone()

                cursor.execute('''
                    SELECT COUNT(*), MAX(updated_at)
                    FROM push_review_log
                    WHERE project_name = ?
                ''', (normalized_name,))
                push_count, push_last = cursor.fetchone()

                cursor.execute('SELECT * FROM project_webhook_config WHERE project_name = ?', (normalized_name,))
                row = cursor.fetchone()
                webhook_config = None
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    webhook_config = ReviewService._format_project_webhook_record(columns, row)

            mr_count = int(mr_count or 0)
            push_count = int(push_count or 0)
            last_review_at = max(filter(None, [
                int(mr_last or 0) if mr_last else None,
                int(push_last or 0) if push_last else None
            ])) if (mr_last or push_last) else None

            if mr_count == 0 and push_count == 0 and not webhook_config:
                return None

            return {
                'project_name': normalized_name,
                'mr_review_count': mr_count,
                'push_review_count': push_count,
                'total_review_count': mr_count + push_count,
                'last_review_at': last_review_at,
                'webhook_config': webhook_config,
                'webhook_enabled_channels': ReviewService._build_enabled_channels(webhook_config)
            }
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving project summary: {e}")
            return None

    @staticmethod
    def delete_project_webhook_config(project_name: str):
        """删除项目webhook配置"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM project_webhook_config WHERE project_name = ?
                ''', (project_name,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.DatabaseError as e:
            print(f"Error deleting project webhook config: {e}")
            return False

    # ---------------------- 团队管理相关方法 ---------------------- #

    @staticmethod
    def _format_team_record(row) -> Dict:
        """将团队记录转换为字典"""
        if row is None:
            return {}
        if isinstance(row, sqlite3.Row):
            row_dict = dict(row)
        else:
            columns = ['id', 'name', 'webhook_url', 'description', 'created_at', 'updated_at']
            row_dict = dict(zip(columns, row))
        return {
            'id': row_dict.get('id'),
            'name': row_dict.get('name'),
            'webhook_url': row_dict.get('webhook_url'),
            'description': row_dict.get('description'),
            'created_at': row_dict.get('created_at'),
            'updated_at': row_dict.get('updated_at'),
        }

    @staticmethod
    def _get_team_members_map(conn, team_ids: List[int]) -> Dict[int, List[str]]:
        """批量获取团队成员映射"""
        if not team_ids:
            return {}
        placeholders = ','.join(['?'] * len(team_ids))
        cursor = conn.cursor()
        cursor.execute(
            f'''
            SELECT team_id, author
            FROM team_members
            WHERE team_id IN ({placeholders})
            ORDER BY author
            ''',
            team_ids
        )
        result: Dict[int, List[str]] = {}
        for team_id, author in cursor.fetchall():
            result.setdefault(team_id, []).append(author)
        return result

    @staticmethod
    def create_team(name: str, webhook_url: Optional[str] = None, description: Optional[str] = None) -> Optional[Dict]:
        """创建团队"""
        normalized_name = (name or '').strip()
        if not normalized_name:
            raise ValueError("团队名称不能为空。")
        sanitized_webhook = (webhook_url or '').strip() or None
        sanitized_description = (description or '').strip() or None

        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO teams (name, webhook_url, description, created_at, updated_at)
                    VALUES (?, ?, ?, strftime('%s', 'now'), strftime('%s', 'now'))
                    ''',
                    (normalized_name, sanitized_webhook, sanitized_description)
                )
                team_id = cursor.lastrowid
                conn.commit()
                return ReviewService.get_team(team_id, include_members=True)
        except sqlite3.IntegrityError:
            raise ValueError(f"团队名称“{normalized_name}”已存在。")
        except sqlite3.DatabaseError as e:
            print(f"Error creating team: {e}")
            return None

    @staticmethod
    def update_team(team_id: int, name: Optional[str] = None, webhook_url: Optional[str] = None,
                    description: Optional[str] = None) -> Optional[Dict]:
        """更新团队信息"""
        if not team_id:
            raise ValueError("团队ID不能为空。")

        fields = []
        params: List = []

        if name is not None:
            normalized_name = (name or '').strip()
            if not normalized_name:
                raise ValueError("团队名称不能为空。")
            fields.append('name = ?')
            params.append(normalized_name)

        if webhook_url is not None:
            sanitized_webhook = (webhook_url or '').strip() or None
            fields.append('webhook_url = ?')
            params.append(sanitized_webhook)

        if description is not None:
            sanitized_description = (description or '').strip() or None
            fields.append('description = ?')
            params.append(sanitized_description)

        if not fields:
            return ReviewService.get_team(team_id, include_members=True)

        fields.append("updated_at = strftime('%s', 'now')")

        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                set_clause = ', '.join(fields)
                cursor.execute(
                    f'''
                    UPDATE teams
                    SET {set_clause}
                    WHERE id = ?
                    ''',
                    (*params, team_id)
                )
                if cursor.rowcount == 0:
                    return None
                conn.commit()
                return ReviewService.get_team(team_id, include_members=True)
        except sqlite3.IntegrityError:
            if name is not None:
                normalized_name = (name or '').strip()
                raise ValueError(f"团队名称“{normalized_name}”已存在。")
            raise
        except sqlite3.DatabaseError as e:
            print(f"Error updating team: {e}")
            return None

    @staticmethod
    def delete_team(team_id: int) -> bool:
        """删除团队（自动删除成员关联）"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    DELETE FROM teams WHERE id = ?
                    ''',
                    (team_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.DatabaseError as e:
            print(f"Error deleting team: {e}")
            return False

    @staticmethod
    def get_team(team_id: int, include_members: bool = False) -> Optional[Dict]:
        """根据ID查询团队"""
        if not team_id:
            raise ValueError("团队ID不能为空。")
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT id, name, webhook_url, description, created_at, updated_at
                    FROM teams
                    WHERE id = ?
                    ''',
                    (team_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None
                team = ReviewService._format_team_record(row)
                if include_members:
                    member_map = ReviewService._get_team_members_map(conn, [team_id])
                    team['members'] = member_map.get(team_id, [])
                return team
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving team: {e}")
            return None

    @staticmethod
    def list_teams(include_members: bool = False) -> List[Dict]:
        """获取团队列表"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT id, name, webhook_url, description, created_at, updated_at
                    FROM teams
                    ORDER BY name
                    '''
                )
                rows = cursor.fetchall()
                teams = [ReviewService._format_team_record(row) for row in rows]
                if include_members and teams:
                    member_map = ReviewService._get_team_members_map(conn, [team['id'] for team in teams])
                    for team in teams:
                        team['members'] = member_map.get(team['id'], [])
                return teams
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving team list: {e}")
            return []

    @staticmethod
    def add_team_members(team_id: int, authors: List[str]) -> int:
        """批量添加团队成员"""
        if not team_id:
            raise ValueError("团队ID不能为空。")
        if not authors:
            return 0

        normalized_authors = []
        for author in authors:
            normalized = (author or '').strip()
            if normalized:
                normalized_authors.append(normalized)

        if not normalized_authors:
            return 0

        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                before_changes = conn.total_changes
                cursor.executemany(
                    '''
                    INSERT INTO team_members (team_id, author, created_at)
                    VALUES (?, ?, strftime('%s', 'now'))
                    ON CONFLICT(author) DO UPDATE SET
                        team_id = excluded.team_id
                    ''',
                    [(team_id, author) for author in normalized_authors]
                )
                conn.commit()
                return conn.total_changes - before_changes
        except sqlite3.DatabaseError as e:
            print(f"Error adding team members: {e}")
            return 0

    @staticmethod
    def remove_team_member(team_id: int, author: str) -> bool:
        """移除团队成员"""
        if not team_id:
            raise ValueError("团队ID不能为空。")
        normalized_author = (author or '').strip()
        if not normalized_author:
            return False
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    DELETE FROM team_members
                    WHERE team_id = ? AND author = ?
                    ''',
                    (team_id, normalized_author)
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.DatabaseError as e:
            print(f"Error removing team member: {e}")
            return False

    @staticmethod
    def get_team_members(team_id: int) -> List[str]:
        """获取团队成员列表"""
        if not team_id:
            raise ValueError("团队ID不能为空。")
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT author
                    FROM team_members
                    WHERE team_id = ?
                    ORDER BY author
                    ''',
                    (team_id,)
                )
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving team members: {e}")
            return []

    @staticmethod
    def get_author_team(author: str) -> Optional[Dict]:
        """根据人员查询团队"""
        normalized_author = (author or '').strip()
        if not normalized_author:
            return None
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT t.id, t.name, t.webhook_url, t.description, t.created_at, t.updated_at
                    FROM team_members tm
                    JOIN teams t ON tm.team_id = t.id
                    WHERE tm.author = ?
                    LIMIT 1
                    ''',
                    (normalized_author,)
                )
                row = cursor.fetchone()
                return ReviewService._format_team_record(row) if row else None
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving author team: {e}")
            return None

    @staticmethod
    def get_author_team_mapping() -> Dict[str, Dict]:
        """获取所有人员所属团队映射"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT tm.author, t.id, t.name, t.webhook_url, t.description
                    FROM team_members tm
                    JOIN teams t ON tm.team_id = t.id
                    '''
                )
                mapping: Dict[str, Dict] = {}
                for row in cursor.fetchall():
                    mapping[row['author']] = {
                        'id': row['id'],
                        'name': row['name'],
                        'webhook_url': row['webhook_url'],
                        'description': row['description'],
                    }
                return mapping
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving author team mapping: {e}")
            return {}

    @staticmethod
    def sync_team_from_gitlab(team_id: int, source_type: str, source_id: str, 
                              gitlab_url: str = None, gitlab_token: str = None,
                              merge_strategy: str = 'replace') -> Dict:
        """
        从 GitLab 同步团队成员
        
        Args:
            team_id: 团队ID
            source_type: 来源类型，'project' 或 'group'
            source_id: GitLab 项目ID或组织ID
            gitlab_url: GitLab URL（可选，默认从环境变量读取）
            gitlab_token: GitLab Token（可选，默认从环境变量读取）
            merge_strategy: 合并策略，'replace'（替换）或 'merge'（合并）
            
        Returns:
            同步结果字典，包含 added, removed, total 等信息
        """
        from biz.gitlab.gitlab_service import GitLabService
        
        if not team_id:
            raise ValueError("团队ID不能为空")
        
        if source_type not in ['project', 'group']:
            raise ValueError("来源类型必须是 'project' 或 'group'")
        
        if not source_id or not source_id.strip():
            raise ValueError("GitLab 项目/组织 ID 不能为空")
        
        # 验证团队是否存在
        team = ReviewService.get_team(team_id)
        if not team:
            raise ValueError(f"团队 ID {team_id} 不存在")
        
        # 初始化 GitLab 服务
        gitlab_service = GitLabService(gitlab_url=gitlab_url, gitlab_token=gitlab_token)
        
        # 根据来源类型获取成员
        if source_type == 'project':
            members = gitlab_service.get_project_members(source_id)
        else:  # group
            members = gitlab_service.get_group_members(source_id)
        
        if members is None:
            raise ValueError(f"无法从 GitLab 获取成员信息，请检查 {source_type} ID 和访问权限")
        
        if not members:
            raise ValueError(f"GitLab {source_type} 中没有找到任何成员")
        
        # 过滤活跃成员，提取用户名
        active_members = [
            m['username'] for m in members 
            if m.get('state') == 'active' and m.get('username')
        ]
        
        if not active_members:
            raise ValueError("没有找到活跃的成员")
        
        # 获取当前团队成员
        current_members = set(ReviewService.get_team_members(team_id))
        new_members = set(active_members)
        
        added_count = 0
        removed_count = 0
        
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                
                if merge_strategy == 'replace':
                    # 替换模式：先删除所有现有成员，再添加新成员
                    cursor.execute('DELETE FROM team_members WHERE team_id = ?', (team_id,))
                    removed_count = cursor.rowcount
                    
                    # 批量插入新成员
                    cursor.executemany(
                        '''
                        INSERT INTO team_members (team_id, author, created_at)
                        VALUES (?, ?, strftime('%s', 'now'))
                        ''',
                        [(team_id, username) for username in active_members]
                    )
                    added_count = cursor.rowcount
                    
                else:  # merge 模式
                    # 添加新成员
                    members_to_add = new_members - current_members
                    if members_to_add:
                        cursor.executemany(
                            '''
                            INSERT INTO team_members (team_id, author, created_at)
                            VALUES (?, ?, strftime('%s', 'now'))
                            ON CONFLICT(author) DO UPDATE SET team_id = excluded.team_id
                            ''',
                            [(team_id, username) for username in members_to_add]
                        )
                        added_count = len(members_to_add)
                
                conn.commit()
            
            # 获取更新后的团队信息
            updated_team = ReviewService.get_team(team_id, include_members=True)
            
            return {
                'success': True,
                'added': added_count,
                'removed': removed_count,
                'total': len(updated_team.get('members', [])),
                'team': updated_team,
                'sync_source': {
                    'type': source_type,
                    'id': source_id
                }
            }
            
        except sqlite3.DatabaseError as e:
            print(f"Error syncing team from GitLab: {e}")
            raise ValueError(f"同步失败：数据库错误 - {str(e)}")


# Initialize database
ReviewService.init_db()
