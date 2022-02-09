import json
import psycopg2


def mark_sold(property):
    connection = psycopg2.connect(user="postgres",
                                  password="a68543520942ef&p",
                                  host="propertybot-dev.co3qp54t8pjo.us-east-1.rds.amazonaws.com",
                                  port="5432",
                                  database="postgres")

    cursor = connection.cursor()

    print("Table Before updating record ", property['property_id'])
    sql_select_query = """select * from properties where external_id = '%s'""" % property['property_id']
    cursor.execute(sql_select_query, property['property_id'])
    record = cursor.fetchone()
    print(record)

    # Update single record now
    sql_update_query = """Update properties set sold_date = '%s' where external_id = '%s'""" % (
        property['sold_date'], property['property_id'])
    cursor.execute(sql_update_query,
                   (property['sold_date'], property['property_id']))
    connection.commit()
    count = cursor.rowcount
    print(count, "Record Updated successfully ")
    cursor.close()
    connection.close()
    print("PostgreSQL connection is closed")


def lambda_handler(event, context):
    for record in event['Records']:
        property = json.loads(record["body"])
        mark_sold(property)
