from telethon import TelegramClient, utils
from telethon import events, Button
from telethon.tl.types import PeerChat, PeerUser
import re
from collections import deque
from os.path import isfile

from email_core import *

import db
from models import Teacher, Student, GroupDelta, GroupsT, UserDelta, UserT

if isfile('config.txt'):
    lines = open('config.txt').readlines()
    for line in lines:
        if re.match(r'ADMIN:(\d+)', line):
            ADMIN = int(re.match(r'ADMIN:(\d+)', line).group(1).strip())
        elif re.match(r'TOKEN:(\w+)', line):
            TOKEN = re.match(r'TOKEN:(\d+:\w+)', line).group(1).strip()
        elif re.match(r'API_ID:(\d+)', line):
            API_ID = int(re.match(r'API_ID:(\d+)', line).group(1).strip())
        elif re.match(r'API_HASH:(\w+)', line):
            API_HASH = re.match(r'API_HASH:(\w+)', line).group(1).strip()
        else:
            print('Necesita configurar el archivo config.txt')
            exit()
else:
    print('Falta el archivo config.txt')
    exit()

bot = TelegramClient('bot_session', API_ID, API_HASH)
bot.start(bot_token=TOKEN)

sess = db.Session_factory()

global msg_cola
global msg_telegram

async def GetEntity(e):
    if e.isdecimal():
        return int(e)
    else:
        try:
            entity = await bot.get_entity(e)
            return entity.id
        except:
            return None

def MakeTo(group_delta):
    to = []
    for s in group_delta.student:
        to.append(s.user_d.email)
    return to

@bot.on(events.NewMessage(pattern=r'/new_teacher', chats=ADMIN))
async def NewTeacher(event):
    text = event.text
    teacher_id = re.match(r'/new_teacher( |_)(\d+|@\w+)', text)
    if teacher_id:
        teacher_id = await GetEntity(teacher_id.group(2))
        if not teacher_id:
            await event.respond('La referencia proporcionada no es válida')
            return

        user = sess.query(UserT).filter(UserT.user_id==teacher_id).first()
        if user:
            teacher = sess.query(Teacher).join(Teacher.user_t).filter(UserT.user_id==teacher_id).first()
            if teacher:
                try:
                    entity = await bot.get_entity(PeerUser(teacher_id))
                    display_name = utils.get_display_name(entity)
                    await event.respond(f'El usuario [{display_name}](tg://user?id={teacher_id}) ya está en la lista de profesores')
                except:
                    await event.respond(f'La referencia proporcionada no es válida')
                return
        else:
            user = UserT(teacher_id)
            sess.add(user)
        new_teacher = Teacher()
        user.teacher = new_teacher

        sess.add(new_teacher)
        sess.commit()
        try:
            entity = await bot.get_entity(PeerUser(teacher_id))
            display_name = utils.get_display_name(entity)
            await event.respond(f'Se ha añadido a [{display_name}](tg://user?id={teacher_id}) como un nuevo profesor')
        except:
            await event.respond(f'El id proporcionado no es válido')
    else:
        await event.respond('Formato incorrecto')

@bot.on(events.NewMessage(pattern=r'/delete_teacher', chats=ADMIN))
async def DeleteTeacher(event):
    text = event.text
    teacher_id = re.match(r'/delete_teacher( |_)(\d+|@\w+)', text)
    if teacher_id:
        teacher_id = await GetEntity(teacher_id.group(2))
        if not teacher_id:
            await event.respond('La referencia proporcionada no es válida')
            return

        teacher = sess.query(Teacher).join(Teacher.user_t).filter(UserT.user_id==teacher_id).first()
        if teacher:
            sess.delete(teacher)
            sess.commit()

            entity = await bot.get_entity(PeerUser(teacher_id))
            display_name = utils.get_display_name(entity)
            await event.respond(f'El usuario [{display_name}](tg://user?id={teacher_id}) ha sido eliminado de la lista de los profesores')
        else:
            try:
                entity = await bot.get_entity(PeerUser(teacher_id))
                display_name = utils.get_display_name(entity)
                await event.respond(f'El usuario [{display_name}](tg://user?id={teacher_id}) no pertenece a la lista de profesores')
            except:
                await event.respond('La referencia proporcionada no es válida')
    else:
        await event.respond('Formato incorrecto')

@bot.on(events.NewMessage(pattern='/show_teacher', chats=ADMIN))
async def ShowTeacher(event):
    teachers = sess.query(Teacher).all()
    m = 'Lista de profesores:\n'
    for t in teachers:
        entity = await bot.get_entity(PeerUser(t.user_t.user_id))
        display_name = utils.get_display_name(entity)
        m += f'[{display_name}](tg://user?id={t.user_t.user_id})       /delete_teacher_{t.user_t.user_id}\n'
    await event.respond(m)

def get_member_by_chat_id(chat_id):
    emails = []
    members = sess.query(Student).join(Student.groups_delta).join(GroupDelta.groups_tele).filter(GroupsT.group_id == chat_id).all()

    for i in members:
        emails.append(i.user_d.email)

    return emails

@bot.on(events.NewMessage(pattern='/new_student'))
async def NewStudent(event):
    user_id = event.sender.id
    is_teacher = sess.query(Teacher).join(Teacher.user_t).filter(UserT.user_id==user_id).first()
    if not is_teacher:
        await event.respond('Usted no tiene permiso para ejecutar ese comando')
        return
    if not event.is_group:
        await event.respond('Debe ejecutar este comando en un grupo')
        return
    new_email = re.match(r'/new_student( |_)([a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)+)', event.text)
    if new_email:
        chat_id = event.message.peer_id.chat_id
        gd = sess.query(GroupDelta).join(GroupDelta.groups_tele).filter(GroupsT.group_id==chat_id).first()
        if not gd:
            gt = GroupsT(chat_id)

            entity = await bot.get_entity(PeerChat(chat_id))
            title = entity.title
            delta_g_id = str(chat_id)

            gd = GroupDelta(delta_g_id, title)
            gd.groups_tele = gt
            gd.teacher.append(is_teacher)

            sess.add(gt)
            sess.add(gd)

        new_email = new_email.group(2)
        user_d = sess.query(UserDelta).filter(UserDelta.email==new_email).first()
        
        if not user_d:
            user_d = UserDelta('', new_email)
            student = Student()
            user_d.student = student

            sess.add(user_d)
            sess.add(student)
            gd.student.append(student)
 
            students_in_chat = get_member_by_chat_id(chat_id)

            if len(students_in_chat) == 1:
                await crear_grupo_delta(bot, event.message, students_in_chat)
            else:
                await anadir_miembro(bot, event.message, students_in_chat, new_email)

            sess.commit()
            await event.respond('Estudiante añadido')

            return
        else:
            groups_this_student = sess.query(GroupDelta).join(GroupDelta.student).join(Student.user_d).filter(UserDelta.email==new_email).all()
            if gd in groups_this_student:
                await event.respond('El estudiante ya pertenece a ese grupo')
            else:
                student = sess.query(Student).join(Student.user_d).filter(UserDelta.email==new_email).first()
                if not student:
                    student = Student()
                    user_d.student = student
                    sess.add(student)

                gd.student.append(student)
                sess.commit()

                students_in_chat = get_member_by_chat_id(chat_id)

                if len(students_in_chat) == 1:
                    await crear_grupo_delta(bot, event.message, students_in_chat)
                else:
                    await anadir_miembro(bot, event.message, students_in_chat, new_email)

                await event.respond('Estudiante añadido')

    else:
        await event.respond('Formato incorrecto')

@bot.on(events.NewMessage(pattern='/delete_student'))
async def DeleteStudent(event):
    user_id = event.sender.id
    is_teacher = sess.query(Teacher).join(Teacher.user_t).filter(UserT.user_id==user_id).first()
    if not is_teacher:
        await event.respond('Usted no tiene permiso para ejecutar ese comando')
        return
    if not event.is_group:
        await event.respond('Debe ejecutar este comando en un grupo')
        return

    del_email = re.match(r'/delete_student( |_)([a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)+)', event.text)
    if del_email:
        chat_id = event.message.peer_id.chat_id
        gd = sess.query(GroupDelta).join(GroupDelta.groups_tele).filter(GroupsT.group_id==chat_id).first()
        if not gd:
            await event.respond('Este grupo no se encuentra en la base de datos')
            return

        del_email = del_email.group(2)
        user_d = sess.query(UserDelta).filter(UserDelta.email==del_email).first()
        
        if not user_d:
            await event.respond(f'El correo {del_email} no se encuentra en la base de datos')
            return
        else:
            groups_this_student = sess.query(GroupDelta).join(GroupDelta.student).join(Student.user_d).filter(UserDelta.email==del_email).all()
            if gd in groups_this_student:
                to = MakeTo(gd)
                if len(to)>1:
                    del gd.student[gd.student.index(user_d.student)]
                    await eliminar_miembro(event.message, to, del_email)

                    sess.commit()
                    await event.respond(f'El estudiante {del_email} ha sido eliminado de este grupo')
                else:
                    del gd.student[0]
                    await eliminar_miembro(event.message, to, del_email)
                    del gd.groups_tele
                    del gd
                    await event.respond("Grupo eliminado")
                    sess.commit()

            else:
                await event.respond(f'El estudiante {del_email} no pertenece a este grupo')

    else:
        await event.respond('Formato incorrecto')

@bot.on(events.NewMessage(pattern='/show_student'))
async def ShowStudent(event):
    user_id = event.sender.id
    chat_id = event.chat.id
    is_teacher = sess.query(Teacher).join(Teacher.user_t).filter(UserT.user_id==user_id).first()
    if not is_teacher:
        await event.respond('Usted no tiene permiso para ejecutar ese comando')
        return
    if not event.is_group:
        await event.respond('Debe ejecutar este comando en un grupo')
        return
    group = sess.query(GroupDelta).join(GroupDelta.groups_tele).filter(GroupsT.group_id==chat_id).first()
    if not group:
        await event.respond('Este grupo no se encuentra en la base de datos')
        return
    student = group.student
    text = 'Lista de estudiantes en este grupo:\n'
    for s in student:
        text += f'{s.user_d.email}     [delete student](http://t.me/share/url?url=/delete_student%20{s.user_d.email})\n'

    await event.respond(text)

@bot.on(events.NewMessage(pattern='/remove_group'))
async def RemoveGroup(event):
    user_id = event.sender.id
    chat_id = event.chat.id
    is_teacher = sess.query(Teacher).join(Teacher.user_t).filter(UserT.user_id==user_id).first()
    if not is_teacher:
        await event.respond('Usted no tiene permiso para ejecutar ese comando')
        return
    if not event.is_group:
        await event.respond('Debe ejecutar este comando en un grupo')
        return
    group = sess.query(GroupDelta).join(GroupDelta.groups_tele).filter(GroupsT.group_id==chat_id).first()
    if not group:
        await event.respond('Este grupo no se encuentra en la base de datos')
        return
    
    to = MakeTo(group)
    for i, s in enumerate(group.student):
        del group.student[i]
        await eliminar_miembro(event.message, to, s.user_d.email)
        del to[0]
    del group.groups_tele
    del group
    await event.respond("Grupo eliminado")
    sess.commit()


@bot.on(events.NewMessage(func=lambda e:e.is_group))
async def toDelta(event):
    print('toDelta')
    groups = sess.query(GroupsT).all()
    groups_ids = []
    for g in groups:
        groups_ids.append(g.group_id)
    chat_id = event.chat.id
    if chat_id in groups_ids and not event.text.startswith('/'):
        group = sess.query(GroupDelta).join(GroupDelta.groups_tele).filter(GroupsT.group_id==chat_id).first()
        if group:
            to = MakeTo(group)
            msg = await classMsgT(event.message, To=to)

            global msg_cola
            msg_cola.append(msg)

#-------------------------------------------------------------
# Email
#-------------------------------------------------------------

# Función para obtener los email provenientes de DeltaChat
def qdelta_imap(conn, server):
    after_date = (datetime.today() - timedelta(1)).strftime('%d-%b-%Y')
    
    
    code, data = conn.search(None, '(HEADER Chat-Version "1.0" SINCE {0})'.format(after_date))
    if code == 'OK':
        for i in data[0].split():
            code, data1 = conn.fetch(i, '(RFC822)')
            if code == 'OK':
                msg = decode_imap_email(data1)
                conn.store(i, "+FLAGS", '\\Deleted')
                action_imap(classMsgR(msg))
            else:
                print('msgs\t', 'could not retrieve email', i)
    elif code == 'NO':
        code, data = conn.search(None, '(SINCE {0})'.format(after_date))
        if code == 'OK':
            for i in data[0].split():
                try:
                    code, data1 = conn.fetch(i, '(BODY.PEEK[HEADER])')
                except Exception as code_data:
                    code = 'NO'
                    print("Error\n\tcode, data1 = conn.fetch(i, '(BODY.PEEK[HEADER])')")
                    print(code_data)
                    print(type(code_data))
                if code == 'OK':
                    msg = decode_imap_email(data1)
                    if msg['Chat-Version'] == '1.0':
                        try:
                            code, data2 = conn.fetch(i, '(RFC822)')
                        except Exception as code_data2:
                            code = 'NO'
                            print("Error\n\tcode, data2 = conn.fetch(i, '(RFC822)')")
                            print(code_data2)
                            print(type(codedata2))
                        if code == 'OK':
                            msg = decode_imap_email(data2)
                            conn.store(i, "+FLAGS", '\\Deleted')
                            action_imap(classMsgR(msg))
    else:
        print('qdelta_imap', 'Could not retrieve emails')
    conn.expunge()

# Función principal para saber que hacer con cada comando
def action_imap(msg_reply):
    global msg_telegram
    
    msg_reply.text = forwaded.sub('', msg_reply.text).strip()
    msg_reply.text = firma.sub('', msg_reply.text).strip()
    

    try:
        if isID(msg_reply.headers['Chat-Group-ID']):
            msg_telegram.append((msg_reply, 'isid'))
        
        else:
            not_recognized = True
            for i in cmd:
                if re.match(i, msg_reply.text) and (not cmd[i][1] or msg_reply.sender in cmd[i][1]):
                    not_recognized = False
                    if not asyncio.coroutines.iscoroutinefunction(cmd[i]):
                        cmd[i][0](msg_reply)
                    else:
                        msg_telegram.append((msg_reply, i))
            if not_recognized and msg_reply.text.startswith('/'):
                cmdNotRecognized(msg_reply)
                
            elif not_recognized:
                onlyText(msg_reply)
                print('Only text')
    except Exception as e:
        print('action_imap')
        print(e)
        print(type(e))

async def toTelegram(msg):
    chats_subcribed = sess.query(GroupsT).all()
    chats_subcribed_ids = []
    for i in chats_subcribed:
        chats_subcribed_ids.append(i.group_id)
    cid = int(msg.msg['Chat-Group-ID'])
    if cid in chats_subcribed_ids:
        text = msg.text
        text = f'```{msg.msg["From"]}:```\n{text}' if text else f'```{msg.msg["From"]}:```'
        if msg.paths == []:
            await bot.send_message(cid, text)
        else:
            print(msg.paths)
            await bot.send_file(cid, msg.paths[0], caption=text)
            first = True
            for pth in msg.paths:
                if not first:
                    await bot.send_file(cid, pth)
                else:
                    first = False

# #-------------------------------------------------------------
# # While True
# #-------------------------------------------------------------

# Función para mantener activa la conexión con el servidor IMAP
def whiletrue_imap(server):
    t = threading.currentThread()
    # sleep(5)
    new_conection = True
    seconds = 1
    while getattr(t, 'do_run', True):
        try:
            if new_conection:
                conn = conn_imap(server)
                qdelta_imap(conn, server)
                new_conection = False
            else:
                code, data = conn.recent()
                if data != [None]:
                    qdelta_imap(conn, server)
                    seconds = 2
                else:
                    # sleep(seconds)
                    if seconds < 30:
                        seconds *= 1.1
        except imaplib.IMAP4.abort:
            new_conection = True
            sleep(5)
    conn.close()
    conn.logout()
    print('Stopping as you wish.')

# Función para mantener la conexión al servidor SMTP
last_send=datetime.now() - timedelta(1)
def whiletrue_smtp(server):
    t = threading.currentThread()
    new_conection = True
    seconds = 2
    global msg_cola
    while getattr(t, 'do_run', True):
        try:
            if new_conection:
                new_conection = False
            else:
                k = 0
                while msg_cola != deque() and k < 10:
                    a = True
                    msg_pop = msg_cola.popleft()
                    while a:
                        try:
                            global last_send
                            send_email(server, msg_pop)
                            last_send = datetime.now()
                            a = False
                        except Exception as excep:
                            print(excep)
                            print(type(excep))
                            a = True
                            sleep(5)
        except Exception as e:
            new_conection = True
            print('whiletrue_smtp')
            print(e)
            sleep(5)
    print('Stopping as you wish.')


# Funcion para ejecutar las funciones asyncrónicas
async def whiletrue_telegram():    
    global msg_telegram
    while True:
        try:
            if msg_telegram != deque():
                msg, action = msg_telegram.popleft()
                if action == 'isid':
                    await toTelegram(msg)
                else:
                    await cmd[action][0](msg)
            else:
                await asyncio.sleep(0.3)
        except Exception as e:
            print('whiletrue_telegram')
            print(type(e))
            print(e)

#-------------------------------------------------------------
#   threads
#-------------------------------------------------------------

t_imap = threading.Thread(target = whiletrue_imap, args=(correo, ), name='imap')
t_smtp = threading.Thread(target = whiletrue_smtp, args=(correo, ), name='smtp')

asyncio.ensure_future(whiletrue_telegram())

t_imap.start()
t_smtp.start()

print('start')
bot.run_until_disconnected()