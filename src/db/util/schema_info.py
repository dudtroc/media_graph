#!/usr/bin/env python3
"""
데이터베이스 스키마 정보 조회 유틸리티
외래키 제약조건 및 테이블 구조 정보를 안전하게 조회합니다.
"""

import psycopg2
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class SchemaInfoChecker:
    """데이터베이스 스키마 정보 조회 클래스"""
    
    def __init__(self):
        """데이터베이스 연결 설정"""
        self.connection_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'scene_graph_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password')
        }
    
    def get_connection(self):
        """데이터베이스 연결 생성"""
        try:
            conn = psycopg2.connect(**self.connection_params)
            return conn
        except Exception as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
            return None
    
    def get_foreign_keys(self) -> List[Dict[str, Any]]:
        """
        외래키 제약조건 정보 조회 (수정된 안전한 쿼리)
        
        Returns:
            List[Dict]: 외래키 정보 목록
        """
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            with conn.cursor() as cursor:
                # 수정된 안전한 쿼리 (컬럼명 모호성 해결)
                query = """
                SELECT 
                    tc.table_name, 
                    kcu.column_name, 
                    tc.constraint_name, 
                    tc.constraint_type,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints tc 
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name 
                JOIN information_schema.constraint_column_usage ccu 
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.table_schema = 'public' 
                    AND tc.constraint_type = 'FOREIGN KEY' 
                ORDER BY tc.table_name, kcu.ordinal_position;
                """
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                foreign_keys = []
                for row in results:
                    foreign_keys.append({
                        'table_name': row[0],
                        'column_name': row[1],
                        'constraint_name': row[2],
                        'constraint_type': row[3],
                        'foreign_table_name': row[4],
                        'foreign_column_name': row[5]
                    })
                
                return foreign_keys
                
        except Exception as e:
            print(f"❌ 외래키 정보 조회 실패: {e}")
            return []
        finally:
            conn.close()
    
    def get_table_info(self) -> List[Dict[str, Any]]:
        """
        테이블 기본 정보 조회
        
        Returns:
            List[Dict]: 테이블 정보 목록
        """
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            with conn.cursor() as cursor:
                query = """
                SELECT 
                    table_name,
                    table_type,
                    is_insertable_into,
                    is_typed
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
                """
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                tables = []
                for row in results:
                    tables.append({
                        'table_name': row[0],
                        'table_type': row[1],
                        'is_insertable_into': row[2],
                        'is_typed': row[3]
                    })
                
                return tables
                
        except Exception as e:
            print(f"❌ 테이블 정보 조회 실패: {e}")
            return []
        finally:
            conn.close()
    
    def get_column_info(self, table_name: str = None) -> List[Dict[str, Any]]:
        """
        컬럼 정보 조회
        
        Args:
            table_name: 특정 테이블명 (None이면 모든 테이블)
            
        Returns:
            List[Dict]: 컬럼 정보 목록
        """
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            with conn.cursor() as cursor:
                if table_name:
                    query = """
                    SELECT 
                        table_name,
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                        AND table_name = %s
                    ORDER BY table_name, ordinal_position;
                    """
                    cursor.execute(query, (table_name,))
                else:
                    query = """
                    SELECT 
                        table_name,
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns 
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position;
                    """
                    cursor.execute(query)
                
                results = cursor.fetchall()
                
                columns = []
                for row in results:
                    columns.append({
                        'table_name': row[0],
                        'column_name': row[1],
                        'data_type': row[2],
                        'is_nullable': row[3],
                        'column_default': row[4],
                        'character_maximum_length': row[5]
                    })
                
                return columns
                
        except Exception as e:
            print(f"❌ 컬럼 정보 조회 실패: {e}")
            return []
        finally:
            conn.close()
    
    def get_index_info(self) -> List[Dict[str, Any]]:
        """
        인덱스 정보 조회
        
        Returns:
            List[Dict]: 인덱스 정보 목록
        """
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            with conn.cursor() as cursor:
                query = """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname;
                """
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                indexes = []
                for row in results:
                    indexes.append({
                        'schema_name': row[0],
                        'table_name': row[1],
                        'index_name': row[2],
                        'index_definition': row[3]
                    })
                
                return indexes
                
        except Exception as e:
            print(f"❌ 인덱스 정보 조회 실패: {e}")
            return []
        finally:
            conn.close()
    
    def print_schema_summary(self):
        """스키마 정보 요약 출력"""
        print("📊 데이터베이스 스키마 정보")
        print("=" * 60)
        
        # 1. 테이블 정보
        tables = self.get_table_info()
        print(f"\n📋 테이블 목록 ({len(tables)}개):")
        for table in tables:
            print(f"  - {table['table_name']} ({table['table_type']})")
        
        # 2. 외래키 정보
        foreign_keys = self.get_foreign_keys()
        print(f"\n🔗 외래키 제약조건 ({len(foreign_keys)}개):")
        for fk in foreign_keys:
            print(f"  - {fk['table_name']}.{fk['column_name']} → {fk['foreign_table_name']}.{fk['foreign_column_name']}")
            print(f"    제약조건명: {fk['constraint_name']}")
        
        # 3. 인덱스 정보
        indexes = self.get_index_info()
        print(f"\n📈 인덱스 목록 ({len(indexes)}개):")
        for idx in indexes:
            print(f"  - {idx['table_name']}.{idx['index_name']}")
        
        print("\n" + "=" * 60)
        print("✅ 스키마 정보 조회 완료!")

def main():
    """메인 실행 함수"""
    checker = SchemaInfoChecker()
    checker.print_schema_summary()

if __name__ == "__main__":
    main()
