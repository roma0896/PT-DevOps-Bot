import logging, os
import re
import paramiko
import tempfile
import subprocess

import psycopg2
from psycopg2 import Error

from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, ForceReply, InputFile, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext


# Подключаем логирование
logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, encoding='utf-8'
)

logger = logging.getLogger(__name__)

# Подключение .env файла
#dotenv_path = Path('bot.env')
#load_dotenv(dotenv_path=dotenv_path)

TOKEN = os.getenv('TOKEN')

# Функция подключения к серверу для мониторинга
def connect_to_server(host, login, password, port):
    try:
        # Создание объекта SSH клиента
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Подключение к серверу
        client.connect(hostname=host, username=login, password=password, port=port)

        logging.info(f'Успешное подключение к {host}', )
        return client
    except Exception as e:
        logging.error(f'Ошибка подключения к {host}')
        return None

# Функция подключения к БД
def db_connection(db_creds):
    try:
        connection = psycopg2.connect(user=db_creds['DB_USER'],
                                    password=db_creds['DB_PASSWORD'],
                                    host=db_creds['DB_HOST'],
                                    port=db_creds['DB_PORT'],
                                    database=db_creds['DATABASE'])
        cursor = connection.cursor()
        logging.info(f"Соединение с PostgreSQL {db_creds['DB_HOST']} установлено")
        return cursor, connection
    except (Exception, Error) as error:
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
        return 0

# Функция /start
def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')

# Функция /help
def helpCommand(update: Update, context):
    update.message.reply_text('''Доступные команды:
Команды для работы с текстом:
/find_email - Ищет почтовые адреса в тексте
/find_phone_number - Ищет номера телефонов в тексте
/verify_password - Проверяет пароль на сложность
Команды для мониторинга Linux системы:
/get_release - О релизе
/get_uname - Об архетиктуре процессора, хосте, ядре
/get_uptime - О времени работы
/get_df - О файловой системе
/get_free - Об ОЗУ
/get_mpstat - О производительности
/get_w - Об активных пользователях
/get_auths - 10 последних успешных входов
/get_critical - 5 последних критических событий
/get_ps - О запущенных процессах
/get_ss - Об используемых портах
/get_apt_list - Выводит все пакеты или указанный
/get_services - Запущенные сервисы''')

# При вводе чего-то кроме команды
def ops(update: Update, context):
    update.message.reply_text("Я вас не пон(, пожалуйста введите /help, чтобы получить список доступных команд")

## Функции отправки запроса на ввод и передача состояния convHandler
def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')
    return 'findPhoneNumbers'

def findEmailCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска почтовых адресов: ')
    return 'find_Email'

def verify_passwd_Command(update: Update, context):
    update.message.reply_text('Введите пароль: ')
    return 'verify_password'

def get_apt_list_Command(update: Update, context):
    update.message.reply_text('Введите 1 - Если требуется вывести все установленные пакеты.\nВведите название пакета - Если требуется вывести информацию о конкретном пакете')
    return 'apt_monitoring'

# Парсинг номера телефона
def findPhoneNumbers (update: Update, context):
    user_input = update.message.text # Получаем текст, содержащий(или нет) номера телефонов
    phoneNumRegex = re.compile(r'\+?[78][- ]?(?:\(\d{3}\)|\d{3})[- ]?\d{3}[- ]?\d{2}[- ]?\d{2}\b') # Регулярное выражение, для обработки номеров телефона

    phoneNumberList = phoneNumRegex.findall(user_input) # Ищем номера телефонов

    if not phoneNumberList: # Обрабатываем случай, когда номеров телефонов нет
        update.message.reply_text('Телефонные номера не найдены, чтобы попробовать поиск снова введите команду ещё раз')
        return ConversationHandler.END# Завершаем выполнение функции

    phoneNumbers = '' # Создаем строку, в которую будем записывать номера телефонов
    for i in range(len(phoneNumberList)):
        phoneNumbers += f'{i+1}. {phoneNumberList[i]}\n' # Записываем очередной номер

    update.message.reply_text(phoneNumbers) # Отправляем сообщение пользователю
    update.message.reply_text("Хотите записать найденные номера телефонов в базу данных?",
                          reply_markup=ReplyKeyboardMarkup([['Да'], ['Нет']], resize_keyboard=True))
    context.user_data['phones_list'] = phoneNumberList
    return 'confirm_save_phones'

# Парсинг почты
def find_Email(update: Update, context):
    user_input = update.message.text # Получаем текст, содержащий (или нет) адреса электронной почты
    email_Regex = re.compile(r'\b[a-zA-Z0-9._%+-]+(?<!\.\.)@[a-zA-Z0-9.-]+(?<!\.)\.[a-zA-Z]{2,}\b') # Регулярное выражение, для поиска почтового адреса

    email_list = email_Regex.findall(user_input) # Ищем адреса email

    if not email_list:
        update.message.reply_text('Email адреса не найдены, чтобы попробовать поиск снова введите команду ещё раз')
        return ConversationHandler.END# Завершаем выполнение функции

    emails = ''
    for i in range(len(email_list)):
        emails += f'{i+1}. {email_list[i]}\n' # Записываем адреса
    update.message.reply_text(emails) # Отправка сообщения пользователю
    update.message.reply_text("Хотите записать найденные email адреса в базу данных?",
                          reply_markup=ReplyKeyboardMarkup([['Да'], ['Нет']], resize_keyboard=True))
    context.user_data['email_list'] = email_list
    return 'confirm_save_emails'

# Проверка сложности пароля
def verify_passwd(update: Update, context):
    user_input = update.message.text # Получаем пароль от пользователя
    passwd_reg = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()]).{8,}$') # Регулярное выражение, для определения сложности пароля

    if bool(re.match(passwd_reg, user_input)):
        update.message.reply_text('Пароль сложный')
        return ConversationHandler.END
    else:
        update.message.reply_text('Пароль простой')
        return ConversationHandler.END

def monitoring(update: Update, context: CallbackContext):
    client = context.bot_data['client']
    command = update.message.text.split()[0]
    match command:
        # Выполнение полученной команды
        case '/get_release':
            stdin, stdout, stderr = client.exec_command('cat /etc/*-release')
            output = stdout.read().decode()
        case '/get_uname':
            stdin, stdout, stderr = client.exec_command('uname -a')
            output = stdout.read().decode()
        case '/get_uptime':
            stdin, stdout, stderr = client.exec_command('uptime -p')
            output = stdout.read().decode()
        case '/get_df':
            stdin, stdout, stderr = client.exec_command('df -hT')
            output = stdout.read().decode()
        case '/get_free':
            stdin, stdout, stderr = client.exec_command('free -h')
            output = stdout.read().decode()
        case '/get_mpstat':
            stdin, stdout, stderr = client.exec_command('iostat')
            output = stdout.read().decode()
            logging.error(stderr.read().decode())
        case '/get_w':
            stdin, stdout, stderr = client.exec_command('w')
            output = stdout.read().decode()
        case '/get_auths':
            stdin, stdout, stderr = client.exec_command('last -n 10')
            output = stdout.read().decode()
        case '/get_critical':
            stdin, stdout, stderr = client.exec_command('journalctl -n 5 -p crit')
            output = stdout.read().decode()
        case '/get_ps':
            stdin, stdout, stderr = client.exec_command('ps au')
            output = stdout.read().decode()
        case '/get_ss':
            stdin, stdout, stderr = client.exec_command('ss -tulpn')
            output = stdout.read().decode()
        case '/get_services':
            stdin, stdout, stderr = client.exec_command('systemctl list-units --type=service --state=running')
            output = stdout.read().decode()
        case '/get_repl_logs':
            execute = 'cat /var/log/postgresql/postgresql-14-main.log | grep -i repl | tail -15'
            #stdin, stdout, stderr = client.exec_command('cat /var/log/postgresql/postgresql-15-main.log | grep -i repl | tail -15') ## Сбор логов репликации
            sproc = subprocess.Popen(execute, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = sproc.communicate()
            if error:
                update.message.reply_text("Ошибка при выполнении команды: " + error.decode())
                logging.error(f'Ошибка при выполнении команды:' + error.decode())
            else:
                update.message.reply_text(output.decode())
        case _:
            return 0
    # Вывод
    update.message.reply_text(output)
    return

# Отправка текстового файла
def send_file(update, file_path):
    chat_id = update.message.chat_id
    with open(file_path, 'rb') as file:
        update.message.reply_document(document=file)

    os.remove(file_path)

# Вывод списка пакетов
def monitoring_packages(update: Update, context: CallbackContext):
    client = context.bot_data['client']
    distr = context.bot_data['distr_os']
    user_input = update.message.text
    output = None
    if user_input == '1':
        if 'debian' in distr:
            stdin, stdout, stderr = client.exec_command("apt list --installed")
        elif 'redhat' in distr:
            stdin, stdout, stderr = client.exec_command("rpm -qa")
        output = stdout.read().decode()
        if len(output) > 4096:
            update.message.reply_text('Ой, вывод слишком большой!\nРезультат работы будет выведен файлом')
            file_path = 'packages.txt'
            with open(file_path, 'w') as file:
                file.write(output)
            send_file(update, file_path)
        else:
            update.message.reply_text(output)
    else:
        if 'debian' in distr:
            stdin, stdout, stderr = client.exec_command(f'dpkg -s {user_input}')
        elif 'redhat' in distr:
            stdin, stdout, stderr = client.exec_command(f'rpm -qi {user_input}')
        output = stdout.read().decode()
        if output: update.message.reply_text(output)
        else: update.message.reply_text('Ой, кажется такой пакет не найден')
    return ConversationHandler.END

# Добавление email адресов в таблицу email
def confirm_save_emails(update: Update, context: CallbackContext):
    user_choice = update.message.text
    if user_choice == 'Да':
        email_list = context.user_data.get('email_list', [])
        db_creds = context.bot_data['db_credentials']
        cursor, connection = db_connection(db_creds)
        inserted_rows = 0
        logging.info(f"Список адресов {email_list}")
        for email in email_list:
            cursor.execute(f"INSERT INTO emails (email) VALUES ('{email}');")
            if cursor.rowcount > 0:
                inserted_rows += 1

        connection.commit()
        cursor.close
        connection.close
        logging.info("Соединение с PostgreSQL закрыто")
        if inserted_rows > 0:
            update.message.reply_text(f'{inserted_rows} email адресов были успешно добавлены в базу данных.', reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text('Не удалось сохранить email адреса в базу данных.', reply_markup=ReplyKeyboardRemove())

    else:
        update.message.reply_text('Сохранение отменено.', reply_markup=ReplyKeyboardRemove())
    context.user_data['email_list'] = []
    return ConversationHandler.END

# Добавление номера телефона в таблицу phones
def confirm_save_phones(update: Update, context: CallbackContext):
    user_choice = update.message.text
    if user_choice == 'Да':
        phones_list = context.user_data.get('phones_list', [])
        db_creds = context.bot_data['db_credentials']
        cursor, connection = db_connection(db_creds)
        inserted_rows = 0
        logging.info(f"Список телефонов {phones_list}")
        for phone in phones_list:
            cursor.execute(f"INSERT INTO phones (phone) VALUES ('{phone}');")
            if cursor.rowcount > 0:
                inserted_rows += 1

        connection.commit()
        cursor.close
        connection.close
        logging.info("Соединение с PostgreSQL закрыто")
        if inserted_rows > 0:
            update.message.reply_text(f'{inserted_rows} номеров телефонов адресов были успешно добавлены в базу данных.', reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text('Не удалось сохранить телефоны в базу данных.', reply_markup=ReplyKeyboardRemove())

    else:
        update.message.reply_text('Сохранение отменено.', reply_markup=ReplyKeyboardRemove())
    context.user_data['email_list'] = []
    return ConversationHandler.END


# Функция для работы с DB
def db_requests(update: Update, context: CallbackContext):
    db_creds = context.bot_data['db_credentials']
    command = update.message.text.split()[0]
    # Инициируем функцию подключения к БД
    cursor, connection = db_connection(db_creds)
    match command:
        # Выполнение полученной команды
        case '/get_emails':
            cursor.execute("SELECT * FROM emails;")
            formatted_data = "Email адреса в DB:\n"
        case '/get_phone_numbers':
            cursor.execute("SELECT * FROM phones;")
            formatted_data = "Номера телефонов в DB:\n"
        case '-':
            cursor.close()
            connection.close()
            return 0
    data = cursor.fetchall()
    # Закрываем соединение с БД
    cursor.close()
    connection.close()
    logging.info("Соединение с PostgreSQL закрыто")

    # Парсинг полученных данных, чтобы вывести в более читаемом виде
    for index, item in enumerate(data, start=1):
        formatted_data += f"{index}. {item[1]}\n"

    # Вывод пользователю бота
    update.message.reply_text(formatted_data)

def main():

    # Данные для подключения по SSH
    host = os.getenv('HOST')
    login = os.getenv('USER')
    password = os.getenv('PASSWORD')
    port = os.getenv('PORT')

    # Подключения к серверу
    client = connect_to_server(host, login, password, port)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    stdin, stdout, stderr = client.exec_command('cat /etc/os-release')
    distr_os = stdout.read().decode().lower()

    # Данные для подключения к DB
    db_credentials = {
        'DB_HOST': os.getenv('DB_HOST'),
        'DB_USER': os.getenv('DB_USER'),
        'DB_PASSWORD': os.getenv('DB_PASSWORD'),
        'DB_PORT': os.getenv('DB_PORT'),
        'DATABASE': os.getenv('DATABASE')
    }

    updater = Updater(TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher
    dp.bot_data['client'] = client
    dp.bot_data['distr_os'] = distr_os
    dp.bot_data['db_credentials'] = db_credentials

    # entry_points для обработчика диалогов
    find_phone_number_handler = CommandHandler('find_phone_number', findPhoneNumbersCommand)
    find_email_handler = CommandHandler('find_email', findEmailCommand)
    password_handler = CommandHandler('verify_password', verify_passwd_Command)
    monitoring_apt = CommandHandler('get_apt_list', get_apt_list_Command)

    # Обработчик диалога для адресов, телефонов, и мониторинга пакетов
    convHandler = ConversationHandler(
        entry_points=[find_phone_number_handler, find_email_handler, password_handler, monitoring_apt],
        states={
            'findPhoneNumbers': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            'find_Email': [MessageHandler(Filters.text & ~Filters.command, find_Email)],
            'verify_password': [MessageHandler(Filters.text & ~Filters.command, verify_passwd)],
            'apt_monitoring': [MessageHandler(Filters.text & ~Filters.command, monitoring_packages)],
            'confirm_save_emails': [MessageHandler(Filters.text & ~Filters.command, confirm_save_emails)],
            'confirm_save_phones': [MessageHandler(Filters.text & ~Filters.command, confirm_save_phones)]
        },
        fallbacks=[]
    )

        ## Регистрируем обработчики команд
    # Команды для работы с текстом
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))
    dp.add_handler(convHandler)

    # Команды для мониторинга Linux системы
    mon_cmd_list = ["get_release", "get_uname", "get_uptime", "get_df", "get_free", "get_mpstat", "get_w", "get_auths", "get_critical", "get_ps", "get_ss", "get_services", "get_repl_logs"]
    dp.add_handler(CommandHandler(mon_cmd_list, monitoring, pass_args=True))


    # Команды для работы с БД
    db_cmd_list = ["get_emails", "get_phone_numbers"]
    dp.add_handler(CommandHandler(db_cmd_list, db_requests, pass_args=True))


        # Регистрируем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, ops))

        # Запускаем бота
    updater.start_polling()

        # Останавливаем бота при нажатии Ctrl+C
    updater.idle()
    client.close()


if __name__ == '__main__':
    main()
