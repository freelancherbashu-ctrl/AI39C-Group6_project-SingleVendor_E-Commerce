import pymysql
pymysql.install_as_MySQLdb()

from flask_mysqldb import MySQL
from flask_mail import Mail

mysql = MySQL()
mail  = Mail()