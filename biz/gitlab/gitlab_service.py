"""
GitLab API 服务
提供 GitLab 项目和组织成员同步功能
"""
import os
from typing import List, Dict, Optional
from urllib.parse import urljoin
import requests

from biz.utils.log import logger


class GitLabService:
    """GitLab API 客户端服务"""
    
    # GitLab 角色到系统角色的映射
    ROLE_MAPPING = {
        50: 'Owner',          # Owner
        40: 'Maintainer',     # Maintainer
        30: 'Developer',      # Developer
        20: 'Reporter',       # Reporter
        10: 'Guest',          # Guest
    }
    
    def __init__(self, gitlab_url: str = None, gitlab_token: str = None):
        """
        初始化 GitLab 服务
        
        Args:
            gitlab_url: GitLab 实例 URL，如果不提供则从环境变量读取
            gitlab_token: GitLab 访问令牌，如果不提供则从环境变量读取
        """
        self.gitlab_url = (gitlab_url or os.getenv('GITLAB_URL', 'https://gitlab.com')).rstrip('/')
        self.gitlab_token = gitlab_token or os.getenv('GITLAB_ACCESS_TOKEN', '')
        
        if not self.gitlab_token:
            logger.warning("GitLab access token not configured. Some features may not work.")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取 API 请求头"""
        return {
            'Private-Token': self.gitlab_token,
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[List]:
        """
        执行 API 请求并处理分页
        
        Args:
            endpoint: API 端点
            params: 请求参数
            
        Returns:
            API 响应数据列表
        """
        if not self.gitlab_token:
            logger.error("GitLab access token is required for API requests")
            return None
        
        url = urljoin(f"{self.gitlab_url}/", endpoint)
        headers = self._get_headers()
        all_results = []
        page = 1
        per_page = 100
        
        if params is None:
            params = {}
        
        params['per_page'] = per_page
        
        try:
            while True:
                params['page'] = page
                logger.debug(f"Requesting GitLab API: {url}, page: {page}")
                response = requests.get(url, headers=headers, params=params, verify=False, timeout=30)
                
                if response.status_code != 200:
                    logger.error(f"GitLab API request failed: {response.status_code}, {response.text}")
                    return None
                
                data = response.json()
                if not data:
                    break
                
                all_results.extend(data)
                
                # 检查是否还有更多页
                if len(data) < per_page:
                    break
                
                page += 1
                
                # 安全限制：最多获取 1000 个成员
                if len(all_results) >= 1000:
                    logger.warning("Reached maximum limit of 1000 members")
                    break
            
            logger.info(f"Successfully fetched {len(all_results)} items from GitLab")
            return all_results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to GitLab API failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error when calling GitLab API: {str(e)}")
            return None
    
    def get_project_members(self, project_id: str) -> Optional[List[Dict]]:
        """
        获取项目成员列表
        
        Args:
            project_id: 项目 ID 或路径（如 "group/project"）
            
        Returns:
            成员列表，每个成员包含 username, name, email, access_level 等信息
        """
        endpoint = f"api/v4/projects/{requests.utils.quote(project_id, safe='')}/members/all"
        members_data = self._make_request(endpoint)
        
        if members_data is None:
            return None
        
        # 格式化成员信息
        members = []
        for member in members_data:
            member_info = {
                'id': member.get('id'),
                'username': member.get('username'),
                'name': member.get('name'),
                'email': member.get('email', member.get('public_email', '')),
                'access_level': member.get('access_level'),
                'access_level_name': self.ROLE_MAPPING.get(member.get('access_level', 0), 'Unknown'),
                'state': member.get('state', 'active'),
                'avatar_url': member.get('avatar_url', '')
            }
            members.append(member_info)
        
        logger.info(f"Found {len(members)} members in project {project_id}")
        return members
    
    def get_group_members(self, group_id: str) -> Optional[List[Dict]]:
        """
        获取组织成员列表
        
        Args:
            group_id: 组织 ID 或路径
            
        Returns:
            成员列表，每个成员包含 username, name, email, access_level 等信息
        """
        endpoint = f"api/v4/groups/{requests.utils.quote(group_id, safe='')}/members/all"
        members_data = self._make_request(endpoint)
        
        if members_data is None:
            return None
        
        # 格式化成员信息
        members = []
        for member in members_data:
            member_info = {
                'id': member.get('id'),
                'username': member.get('username'),
                'name': member.get('name'),
                'email': member.get('email', member.get('public_email', '')),
                'access_level': member.get('access_level'),
                'access_level_name': self.ROLE_MAPPING.get(member.get('access_level', 0), 'Unknown'),
                'state': member.get('state', 'active'),
                'avatar_url': member.get('avatar_url', '')
            }
            members.append(member_info)
        
        logger.info(f"Found {len(members)} members in group {group_id}")
        return members
    
    def verify_project_access(self, project_id: str) -> bool:
        """
        验证是否有权访问指定项目
        
        Args:
            project_id: 项目 ID 或路径
            
        Returns:
            是否有访问权限
        """
        endpoint = f"api/v4/projects/{requests.utils.quote(project_id, safe='')}"
        url = urljoin(f"{self.gitlab_url}/", endpoint)
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to verify project access: {str(e)}")
            return False
    
    def verify_group_access(self, group_id: str) -> bool:
        """
        验证是否有权访问指定组织
        
        Args:
            group_id: 组织 ID 或路径
            
        Returns:
            是否有访问权限
        """
        endpoint = f"api/v4/groups/{requests.utils.quote(group_id, safe='')}"
        url = urljoin(f"{self.gitlab_url}/", endpoint)
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to verify group access: {str(e)}")
            return False
    
    def get_user_projects(self, owned: bool = False, membership: bool = True) -> Optional[List[Dict]]:
        """
        获取用户有权访问的项目列表
        
        Args:
            owned: 是否只获取用户拥有的项目
            membership: 是否只获取用户是成员的项目
            
        Returns:
            项目列表，每个项目包含 id, name, path_with_namespace 等信息
        """
        endpoint = "api/v4/projects"
        params = {
            'simple': True,  # 只返回简化信息
            'order_by': 'last_activity_at',
            'sort': 'desc'
        }
        
        if owned:
            params['owned'] = 'true'
        if membership:
            params['membership'] = 'true'
        
        projects_data = self._make_request(endpoint, params)
        
        if projects_data is None:
            return None
        
        # 格式化项目信息
        projects = []
        for project in projects_data:
            project_info = {
                'id': project.get('id'),
                'name': project.get('name'),
                'path': project.get('path'),
                'path_with_namespace': project.get('path_with_namespace'),
                'description': project.get('description', ''),
                'web_url': project.get('web_url'),
                'namespace': project.get('namespace', {}),
                'visibility': project.get('visibility', 'private'),
                'last_activity_at': project.get('last_activity_at'),
                'created_at': project.get('created_at')
            }
            projects.append(project_info)
        
        logger.info(f"Found {len(projects)} projects")
        return projects
    
    def get_group_projects(self, group_id: str, include_subgroups: bool = True) -> Optional[List[Dict]]:
        """
        获取组织下的项目列表
        
        Args:
            group_id: 组织 ID 或路径
            include_subgroups: 是否包含子组织的项目
            
        Returns:
            项目列表
        """
        endpoint = f"api/v4/groups/{requests.utils.quote(group_id, safe='')}/projects"
        params = {
            'simple': True,
            'order_by': 'last_activity_at',
            'sort': 'desc'
        }
        
        if include_subgroups:
            params['include_subgroups'] = 'true'
        
        projects_data = self._make_request(endpoint, params)
        
        if projects_data is None:
            return None
        
        # 格式化项目信息
        projects = []
        for project in projects_data:
            project_info = {
                'id': project.get('id'),
                'name': project.get('name'),
                'path': project.get('path'),
                'path_with_namespace': project.get('path_with_namespace'),
                'description': project.get('description', ''),
                'web_url': project.get('web_url'),
                'namespace': project.get('namespace', {}),
                'visibility': project.get('visibility', 'private'),
                'last_activity_at': project.get('last_activity_at'),
                'created_at': project.get('created_at')
            }
            projects.append(project_info)
        
        logger.info(f"Found {len(projects)} projects in group {group_id}")
        return projects
