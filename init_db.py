import mysql.connector
from mysql.connector import errorcode

# Database config
config = {
    'user': 'root',
    'password': 'student',
    'host': 'localhost',
    'port': '3306'
}

DB_NAME = 'cropguard'

TABLES = {}
TABLES['users'] = (
    "CREATE TABLE `users` ("
    "  `id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `name` varchar(255) NOT NULL,"
    "  `email` varchar(255) NOT NULL UNIQUE,"
    "  `password` varchar(255) NOT NULL,"
    "  `role` varchar(20) DEFAULT 'user',"
    "  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,"
    "  PRIMARY KEY (`id`)"
    ") ENGINE=InnoDB"
)

TABLES['crops'] = (
    "CREATE TABLE `crops` ("
    "  `id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `name` varchar(100) NOT NULL,"
    "  `scientific_name` varchar(100),"
    "  `category` varchar(50),"
    "  `season` varchar(50),"
    "  `soil_type` varchar(100),"
    "  `water_requirement` varchar(100),"
    "  `climate` varchar(100),"
    "  `temperature_range` varchar(50),"
    "  `humidity` varchar(50),"
    "  `sunlight` varchar(100),"
    "  `description` text,"
    "  `image` varchar(255),"
    "  PRIMARY KEY (`id`)"
    ") ENGINE=InnoDB"
)

TABLES['predictions'] = (
    "CREATE TABLE `predictions` ("
    "  `id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `user_id` int(11) NOT NULL,"
    "  `image_name` varchar(255),"
    "  `image_path` varchar(255),"
    "  `result` varchar(255),"
    "  `confidence` float,"
    "  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,"
    "  PRIMARY KEY (`id`),"
    "  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE"
    ") ENGINE=InnoDB"
)

def create_database(cursor):
    try:
        cursor.execute(
            "CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8'".format(DB_NAME))
    except mysql.connector.Error as err:
        print("Failed creating database: {}".format(err))
        exit(1)

def setup_db():
    print("Connecting to MySQL server...")
    try:
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor()
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        else:
            print(err)
        exit(1)

    try:
        cursor.execute("USE {}".format(DB_NAME))
        print(f"Using database '{DB_NAME}'")
    except mysql.connector.Error as err:
        print("Database {} does not exist.".format(DB_NAME))
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            create_database(cursor)
            print("Database {} created successfully.".format(DB_NAME))
            cnx.database = DB_NAME
        else:
            print(err)
            exit(1)

    for table_name in TABLES:
        table_description = TABLES[table_name]
        try:
            print("Creating table {}: ".format(table_name), end='')
            cursor.execute(table_description)
            print("OK")
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("already exists.")
            else:
                print(err.msg)

    cursor.close()
    cnx.close()
    print("Database setup complete.")

if __name__ == '__main__':
    setup_db()
