import pymysql
pymysql.install_as_MySQLdb()

from flask_mysqldb import MySQL
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect

mysql = MySQL()
mail  = Mail()
csrf  = CSRFProtect()