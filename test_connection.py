from database import get_connection

try:
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM orders;")

    result = cursor.fetchone()

    print("Connection successful!")
    print("Number of orders:", result[0])

    cursor.close()
    connection.close()

except Exception as e:
    print("Connection failed!")
    print(e)