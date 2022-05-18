import json
import base64
from algosdk import account, mnemonic, constants
from algosdk.v2client import algod
from algosdk.future import transaction
import os


def first_transaction_example(private_key, my_address):
   
    algo_address_local = "http://localhost:4001"
    algod_address = "https://testnet-api.algonode.cloud"
    algod_token = ""
    algod_client = algod.AlgodClient(algod_token, algod_address)

    account_info = algod_client.account_info(my_address)
    print("Account balance: {} microAlgos".format(account_info.get('amount')))

    # build transaction
    params = algod_client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = constants.MIN_TXN_FEE
    params.fee = 1000
    receiver = "HZ57J3K46JIJXILONBBZOHX6BKPXEM2VVXNRFSUED6DKFD5ZD24PMJ3MVA"
    amount = 0
    #note = "Hello World".encode()

    unsigned_txn = transaction.PaymentTxn(my_address, params, receiver, amount, None)

    # sign transaction
    signed_txn = unsigned_txn.sign(private_key)

    # submit transaction
    txid = algod_client.send_transaction(signed_txn)
    # print("Signed transaction with txID: {}".format(txid))

    # wait for confirmation
    try:
        confirmed_txn = transaction.wait_for_confirmation(algod_client, txid, 4)
    except Exception as err:
        print(err)
    #account_info = algod_client.account_info(my_address)
    return txid


""" print("Transaction information: {}".format(json.dumps(confirmed_txn, indent=4)))
 print("Decoded note: {}".format(base64.b64decode(
     confirmed_txn["txn"]["txn"]["note"]).decode()))

 print("Starting Account balance: {} microAlgos".format(account_info.get('amount')) )
 print("Amount transfered: {} microAlgos".format(amount) )
 print("Fee: {} microAlgos".format(params.fee) )"""
# print("Final Account balance: {} microAlgos".format(account_info.get('amount')) + "\n")
