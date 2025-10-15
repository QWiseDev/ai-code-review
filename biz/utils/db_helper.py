"""
数据库操作辅助工具
提供统一的数据库连接管理、错误处理和日志记录
"""
import  sqlite3
from  contextlib  contextmanager
from  typing  import  Any,  List,  Optional,  Tuple
from  biz.utils.log  import  logger


class  DatabaseError(Exception):
                """数据库操作错误"""
                pass


class  DatabaseHelper:
                """数据库操作辅助类"""

                @staticmethod
                @contextmanager
                def  get_connection(db_file:  str,  enable_foreign_keys:  bool  =  True):
                                """
                                获取数据库连接的上下文管理器

                                Args:
                                                db_file:  数据库文件路径
                                                enable_foreign_keys:  是否启用外键约束

                                Yields:
                                                sqlite3.Connection:  数据库连接对象
                                """
                                conn  =  None
                                try:
                                                conn  =  sqlite3.connect(db_file,  timeout=10.0)
                                                conn.row_factory  =  sqlite3.Row
                                                if  enable_foreign_keys:
                                                                conn.execute('PRAGMA  foreign_keys  =  ON;')
                                                yield  conn
                                except  sqlite3.Error  as  e:
                                                logger.error(f"数据库连接错误:  {e}",  exc_info=True)
                                                raise  DatabaseError(f"数据库连接失败:  {e}")  from  e
                                finally:
                                                if  conn:
                                                                conn.close()

                @staticmethod
                def  execute_query(
                                db_file:  str,
                                query:  str,
                                params:  Tuple  =  (),
                                fetch_one:  bool  =  False,
                                fetch_all:  bool  =  True
                )  ->  Any:
                                """
                                执行查询并返回结果

                                Args:
                                                db_file:  数据库文件路径
                                                query:  SQL查询语句
                                                params:  查询参数
                                                fetch_one:  是否只获取一行结果
                                                fetch_all:  是否获取所有结果

                                Returns:
                                                查询结果
                                """
                                try:
                                                with  DatabaseHelper.get_connection(db_file)  as  conn:
                                                                cursor  =  conn.cursor()
                                                                cursor.execute(query,  params)
                                                                if  fetch_one:
                                                                                return  cursor.fetchone()
                                                                elif  fetch_all:
                                                                                return  cursor.fetchall()
                                                                return  None
                                except  sqlite3.Error  as  e:
                                                logger.error(f"查询执行失败:  {query}  |  参数:  {params}  |  错误:  {e}",  exc_info=True)
                                                raise  DatabaseError(f"查询执行失败:  {e}")  from  e

                @staticmethod
                def  execute_update(
                                db_file:  str,
                                query:  str,
                                params:  Tuple  =  (),
                                commit:  bool  =  True
                )  ->  int:
                                """
                                执行更新操作（INSERT、UPDATE、DELETE）

                                Args:
                                                db_file:  数据库文件路径
                                                query:  SQL语句
                                                params:  参数
                                                commit:  是否自动提交

                                Returns:
                                                int:  受影响的行数
                                """
                                try:
                                                with  DatabaseHelper.get_connection(db_file)  as  conn:
                                                                cursor  =  conn.cursor()
                                                                cursor.execute(query,  params)
                                                                if  commit:
                                                                                conn.commit()
                                                                return  cursor.rowcount
                                except  sqlite3.IntegrityError  as  e:
                                                #  完整性约束错误（如唯一键冲突）
                                                logger.warning(f"数据完整性错误:  {query}  |  参数:  {params}  |  错误:  {e}")
                                                raise  ValueError(f"数据完整性错误:  {e}")  from  e
                                except  sqlite3.Error  as  e:
                                                logger.error(f"更新操作失败:  {query}  |  参数:  {params}  |  错误:  {e}",  exc_info=True)
                                                raise  DatabaseError(f"更新操作失败:  {e}")  from  e

                @staticmethod
                def  execute_batch(
                                db_file:  str,
                                query:  str,
                                params_list:  List[Tuple]
                )  ->  int:
                                """
                                批量执行操作

                                Args:
                                                db_file:  数据库文件路径
                                                query:  SQL语句
                                                params_list:  参数列表

                                Returns:
                                                int:  受影响的总行数
                                """
                                if  not  params_list:
                                                return  0

                                try:
                                                with  DatabaseHelper.get_connection(db_file)  as  conn:
                                                                cursor  =  conn.cursor()
                                                                before_changes  =  conn.total_changes
                                                                cursor.executemany(query,  params_list)
                                                                conn.commit()
                                                                return  conn.total_changes  -  before_changes
                                except  sqlite3.IntegrityError  as  e:
                                                logger.warning(f"批量操作数据完整性错误:  {query}  |  错误:  {e}")
                                                raise  ValueError(f"批量操作数据完整性错误:  {e}")  from  e
                                except  sqlite3.Error  as  e:
                                                logger.error(f"批量操作失败:  {query}  |  错误:  {e}",  exc_info=True)
                                                raise  DatabaseError(f"批量操作失败:  {e}")  from  e

                @staticmethod
                def  execute_transaction(db_file:  str,  operations:  List[Tuple[str,  Tuple]])  ->  bool:
                                """
                                在事务中执行多个操作

                                Args:
                                                db_file:  数据库文件路径
                                                operations:  操作列表，每个元素为  (query,  params)  元组

                                Returns:
                                                bool:  事务是否成功
                                """
                                try:
                                                with  DatabaseHelper.get_connection(db_file)  as  conn:
                                                                cursor  =  conn.cursor()
                                                                for  query,  params  in  operations:
                                                                                cursor.execute(query,  params)
                                                                conn.commit()
                                                                logger.info(f"事务执行成功，共  {len(operations)}  个操作")
                                                                return  True
                                except  sqlite3.IntegrityError  as  e:
                                                logger.warning(f"事务数据完整性错误:  {e}")
                                                raise  ValueError(f"事务数据完整性错误:  {e}")  from  e
                                except  sqlite3.Error  as  e:
                                                logger.error(f"事务执行失败:  {e}",  exc_info=True)
                                                raise  DatabaseError(f"事务执行失败:  {e}")  from  e
