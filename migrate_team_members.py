#!/usr/bin/env python3
"""
数据库迁移脚本 - 为 team_members 表添加新字段

使用方法:
1. 停止正在运行的应用服务器
2. 运行此脚本: python migrate_team_members.py
3. 重新启动应用服务器

注意: 应用会在启动时自动尝试添加缺失的字段，
      但如果遇到问题，可以手动运行此脚本。
"""
import sqlite3
import os

DB_FILE = "data/data.db"

def migrate_team_members():
    """为 team_members 表添加新字段"""
    if not os.path.exists(DB_FILE):
        print(f"数据库文件 {DB_FILE} 不存在，无需迁移")
        return
    
    print(f"开始迁移数据库: {DB_FILE}")
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # 检查现有字段
            cursor.execute("PRAGMA table_info(team_members)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            print(f"现有字段: {', '.join(existing_columns)}")
            
            # 需要添加的新字段
            new_fields = [
                ('name', 'TEXT'),
                ('email', 'TEXT'),
                ('avatar_url', 'TEXT'),
                ('access_level', 'INTEGER'),
                ('access_level_name', 'TEXT'),
                ('updated_at', 'INTEGER')
            ]
            
            added_count = 0
            for field_name, field_type in new_fields:
                if field_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE team_members ADD COLUMN {field_name} {field_type}")
                        print(f"✓ 成功添加字段: {field_name} ({field_type})")
                        added_count += 1
                    except sqlite3.DatabaseError as e:
                        print(f"✗ 添加字段 {field_name} 失败: {e}")
                else:
                    print(f"- 字段 {field_name} 已存在，跳过")
            
            conn.commit()
            
            # 验证迁移结果
            cursor.execute("PRAGMA table_info(team_members)")
            final_columns = [col[1] for col in cursor.fetchall()]
            print(f"\n迁移完成!")
            print(f"最终字段列表: {', '.join(final_columns)}")
            print(f"共添加 {added_count} 个新字段")
            
    except sqlite3.DatabaseError as e:
        print(f"数据库迁移失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("团队成员表 (team_members) 数据库迁移")
    print("=" * 60)
    migrate_team_members()
