import db

from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy import ForeignKey, Table
from sqlalchemy.orm import relationship

join_teacher_group_delta_table = Table('join_teacher_group_delta', db.Base.metadata, Column('teacher_id', Integer, ForeignKey('teacher.id')), Column('group_delta_id', Integer, ForeignKey('groups_d.id')))

join_student_group_delta_table = Table('join_student_group_delta', db.Base.metadata, Column('student_id', Integer, ForeignKey('student.id')), Column('group_delta_id', Integer, ForeignKey('groups_d.id')))

class Teacher(db.Base):
    __tablename__ = 'teacher'

    id = Column(Integer, primary_key=True)
    
    user_t = relationship('UserT', back_populates='teacher', uselist=False)

    groups_delta = relationship('GroupDelta', secondary=join_teacher_group_delta_table, back_populates='teacher')

    def __init__(self):
        pass

    def __repr__(self):
        return f'teacher(id={self.id})'

    def __str__(self):
        return self.__repr__()

class Student(db.Base):
    __tablename__ = 'student'

    id = Column(Integer, primary_key=True)
    
    user_d = relationship('UserDelta', back_populates='student', uselist=False)

    groups_delta = relationship('GroupDelta', secondary=join_student_group_delta_table, back_populates='student')


    def __init__(self):
        pass

    def __repr__(self):
        return f'student(id={self.id})'

    def __str__(self):
        return self.__repr__()

class GroupDelta(db.Base):
    __tablename__ = 'groups_d'

    id = Column(Integer, primary_key=True)
    GROUP_NAME = Column(String)
    GROUP_ID = Column(String)

    groups_tele = relationship('GroupsT', back_populates='groups_delta', uselist=False)

    teacher = relationship('Teacher', secondary=join_teacher_group_delta_table, back_populates='groups_delta')

    student = relationship('Student', secondary=join_student_group_delta_table, back_populates='groups_delta')


    def __init__(self, GROUP_ID, GROUP_NAME):
        self.GROUP_ID = GROUP_ID
        self.GROUP_NAME = GROUP_NAME

    def __repr__(self):
        return f'groups_d(id={self.id}, GROUP_ID={self.GROUP_ID}, GROUP_NAME={self.GROUP_NAME})'

    def __str__(self):
        return self.__repr__()

class GroupsT(db.Base):
    __tablename__ = 'groups_t'

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer)

    groups_d_id = Column(Integer, ForeignKey('groups_d.id'))

    groups_delta = relationship('GroupDelta', back_populates='groups_tele')

    def __init__(self, group_id):
        self.group_id = group_id

    def __repr__(self):
        return f'groups_t(id={self.id}, group_id={self.group_id})'

    def __str__(self):
        return self.__repr__()

class UserDelta(db.Base):
    __tablename__ = 'user_delta'

    id = Column(Integer, primary_key=True)
    user_name_delta = Column(String)
    email = Column(String)

    student_id = Column(Integer, ForeignKey('student.id'))

    student = relationship('Student', back_populates='user_d')

    def __init__(self, user_name_delta, email):
        self.user_name_delta = user_name_delta
        self.email = email

    def __repr__(self):
        return f'UserDelta(user_name_delta={self.user_name_delta}, email={self.email})'

    def __str__(self):
        return self.__repr__()

class UserT(db.Base):
    __tablename__ = 'user_t'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)

    teacher_id = Column(Integer, ForeignKey('teacher.id'))

    teacher = relationship('Teacher', back_populates='user_t')

    def __init__(self, user_id):
        self.user_id = user_id

    def __repr__(self):
        return f'UserT(id={self.id}, user_id={self.user_id})'

    def __str__(self):
        return self.__repr__()