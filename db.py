import sqlalchemy
from sqlalchemy import Column, String, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session, sessionmaker
from config import Config

__all__ = ['engine', 'DatabaseObject', 'Session', 'Column', 'String', 'ForeignKey', 'relationship', 'BigInteger']

engine = sqlalchemy.create_engine(Config.CONFIG['db_url'])
DatabaseObject = declarative_base(bind=engine, name='DatabaseObject')
DatabaseObject.__table_args__ = {'extend_existing': True} # allow use of the reload command with db cogs


class CtxSession(Session):
	def __enter__(self):
		return self
	
	async def __aenter__(self):
		return self
	
	def __exit__(self, err_type, err, tb):
		if err_type is None:
			self.commit()
		else:
			self.rollback()
		return False
	
	async def __aexit__(self, err_type, err, tb):
		return self.__exit__(err_type, err, tb)


Session = sessionmaker(bind=engine, class_=CtxSession)
