import os
import boto3
import json
import random

from boto3.dynamodb.conditions import Key, Attr

dynamodb_resource = boto3.resource('dynamodb')
dynamodb_table = os.getenv('dynamodb_table')
dynamodb_pk = os.getenv('dynamodb_pk')
dynamodb_sk = os.getenv('dynamodb_sk')

def get_named_parameter(event, name):
    return next(item for item in event['parameters'] if item['name'] == name)['value']
    
def populate_function_response(event, response_body):
    return {'response': {'actionGroup': event['actionGroup'], 'function': event['function'],
                'functionResponse': {'responseBody': {'TEXT': {'body': str(response_body)}}}}}

def put_dynamodb(table_name, item):
    table = dynamodb_resource.Table(table_name)
    
    resp = table.update_item(
        Key={'customer_id': item['customer_id'],
             'item_id': item['item_id']},
        UpdateExpression='SET #attr1 = :val1',
        ExpressionAttributeNames={'#attr1': 'staffing'},
        ExpressionAttributeValues={':val1':  item['staffing']}
    )
    return resp

def read_dynamodb(
    table_name: str, 
    pk_field: str,
    pk_value: str,
    sk_field: str=None, 
    sk_value: str=None,
    attr_key: str=None,
    attr_val: str=None
):
    try:

        table = dynamodb_resource.Table(table_name)
        # Create expression
        if sk_field:
            key_expression = Key(pk_field).eq(pk_value) & Key(sk_field).eq(sk_value)
        else:
            key_expression = Key(pk_field).eq(pk_value)

        if attr_key:
            attr_expression = Attr(attr_key).eq(attr_val)
            query_data = table.query(
                KeyConditionExpression=key_expression,
                FilterExpression=attr_expression
            )
        else:
            query_data = table.query(
                KeyConditionExpression=key_expression
            )
        
        return query_data['Items']
    except Exception:
        print(f'Error querying table: {table_name}.')


def detect_peak_traffic(store_id):
    return read_dynamodb(dynamodb_table, 
                       dynamodb_pk, 
                       store_id, 
                       attr_key="peak", attr_val="True")

def detect_inefficient_processes(store_id):
    return read_dynamodb(dynamodb_table, 
                       dynamodb_pk, 
                       store_id,
                       attr_key="essential", attr_val="False")

                
def redistribute_staffing(store_id, department_id, staffing):
    item = {
        'customer_id': store_id,
        'item_id': department_id,
        'staffing': staffing
    }
    resp = put_dynamodb(dynamodb_table, item)
    return f"Department {department_id} has been updated. New staffing level: {staffing}"


def lambda_handler(event, context):
    print(event)
    
    # name of the function that should be invoked
    function = event.get('function', '')

    # parameters to invoke function with
    parameters = event.get('parameters', [])
    
    store_id = get_named_parameter(event, "store_id")

    if function == 'detect_peak_traffic':    
        result = detect_peak_traffic(store_id)
    elif function == 'detect_inefficient_processes':    
        result = detect_inefficient_processes(store_id)
    elif function == 'redistribute_staffing':    
        department_id = get_named_parameter(event, "department_id")
        staffing = get_named_parameter(event, "staffing")
        result = redistribute_staffing(store_id, department_id, staffing)
    else:
        result = f"Error, function '{function}' not recognized"

    response = populate_function_response(event, result)
    print(response)
    return response