from web3 import Web3
import time

###CONNECT TO ETH NETWORK USING HOSTED NODE (infura)##########
#w3 = Web3(Web3.WebsocketProvider("wss://rinkeby.infura.io/ws/v3/839112f3db884bde86889ebbac153ced"))

###CONNECT TO ETH NETWORK USING LOCAL LIGHT NODE (GETH)##########
#w3 = Web3(Web3.IPCProvider("/home/vagrant/.ethereum/rinkeby/geth.ipc"))

###CONNECT TO POLYGON NETWORK USING HOSTED NODE##########
w3 = Web3(Web3.HTTPProvider("https://rpc-mumbai.matic.today"))


import os
from web3.middleware import geth_poa_middleware
w3.middleware_stack.inject(geth_poa_middleware, layer=0)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/utils/data/"
# '/vagrant/luce_django/luce'
MAIN_CONTRACT_PATH = BASE_DIR + 'Main.sol'
CONSENT_CONTRACT_PATH = BASE_DIR + 'ConsentCode.sol'
REGISTRY_CONTRACT_PATH = BASE_DIR + 'LuceRegistry.sol'

CONTRACT_FILE = "LUCERegistry" 
LUCEMAIN_CONTRACT = "LuceMain"
CONSENT_CONTRACT = "ConsentCode"

CHAIN_ID = 80001

DEBUG = True

#### WEB3 HELPER FUNCTIONS ####g
# Helper functions used to make the code in assign_address_v3 easier to read

# Create faucet for pre-funding accounts
# NOTE: placing a private key here is obviously very unsafe
# We only do this for development usage. When transitioning 
# to Infura the faucet can be replaced with an API call instead.

# Private key (obtained via Ganache interface)
faucet_privateKey   = "52417fb192c8cb46bf2b76e814992a803910d42cd19ca0ae0a83c5de97c6dbd6"

# Establish faucet account
faucet = w3.eth.account.privateKeyToAccount(faucet_privateKey)


def create_wallet():
    eth_account = w3.eth.account.create()
    return (eth_account)


def send_ether(amount_in_ether, recipient_address, sender_pkey):
    amount_in_wei = w3.toWei(amount_in_ether,'ether')

    
    # Obtain sender address from private key
    sender_address = w3.eth.account.privateKeyToAccount(sender_pkey).address

    # How many transactions have been made by wallet?
    # This is required and prevents double-spending.
    # Same name but different from nonce in block mining.
    nonce = w3.eth.getTransactionCount(sender_address)
    # Specify transcation dictionary
    txn_dict = {
            'from':sender_address,
            'to': recipient_address,
            'value': amount_in_wei,
            'gasPrice': w3.toWei('30', 'Gwei'),
            'nonce': nonce,
            'chainId': CHAIN_ID
    }
    
    # IN THIS STEP THE PRIVATE KEY OF THE SENDER IS USED
    # Sign transaction
    gas = w3.eth.estimateGas(txn_dict)
    txn_dict["gas"] = gas
    txn_receipt = sign_and_send(txn_dict, sender_pkey, "sending ether from faucet to account")
    return txn_receipt




#### ASSIGN ADDRESS ####
# This script takes a Django user object as input and
# creates a fresh ethereum account for the user.
# It will also pre-fund the new account with some ether.

def assign_address_v3():
    # Establish web3 connection
    import time
    from hexbytes import HexBytes
    # Create new web3 account
    eth_account = create_wallet()
    txn_receipt = send_ether(amount_in_ether = 0.5, recipient_address = eth_account.address, sender_pkey=faucet.privateKey)
    # Return user, now with wallet associated
    return txn_receipt, eth_account

def check_balance(user):
   
    balance_contract = w3.eth.getBalance(user.contract_address)
    balance_user = w3.eth.getBalance(user.ethereum_public_key)
    final = {
        "contract balance": balance_contract,
        "address balance": balance_user
    }
    return final






def deploy_registry(_user):
    return deploy(_user, REGISTRY_CONTRACT_PATH, CONTRACT_FILE)

def deploy_contract_main(_user):
    return deploy(_user, MAIN_CONTRACT_PATH, LUCEMAIN_CONTRACT)

def deploy_consent(_user):
    return deploy(_user, CONSENT_CONTRACT_PATH, CONSENT_CONTRACT)

def deploy(_user, contract, interface):
    from solcx import compile_source
    from web3 import Web3
    contract_interface = compile_and_extract_interface(contract, interface)

    # Extract abi and bytecode
    abi = contract_interface['abi']
    bytecode = contract_interface['bin']
    contract = w3.eth.contract(abi=abi,bytecode=bytecode)

    # Obtain contract address & instantiate contract

    user_address = _user.ethereum_public_key

    private_key = _user.ethereum_private_key
    nonce = w3.eth.getTransactionCount(user_address)

    txn_dict = {
        'from': user_address,
        'chainId': CHAIN_ID,
        'gasPrice': w3.toWei('20', 'gwei'),
        'nonce': nonce,
        }

    gas = contract.constructor().estimateGas()*2

    txn_dict["gas"]=gas
    contract_txn = contract.constructor().buildTransaction(txn_dict)    

    return sign_and_send(contract_txn, private_key, "deployment of "+interface)



    
def compile_and_extract_interface_Consent():
    return compile_and_extract_interface(CONSENT_CONTRACT_PATH, CONSENT_CONTRACT)

def compile_and_extract_interface_Registry():
    return compile_and_extract_interface(REGISTRY_CONTRACT_PATH, CONTRACT_FILE)

def compile_and_extract_interface_Main():
    return compile_and_extract_interface(MAIN_CONTRACT_PATH, LUCEMAIN_CONTRACT)

def compile_and_extract_interface(contract, interface):
    import solcx
    from solcx import compile_source
    
    # Read in LUCE contract code
    with open(contract, 'r') as file: # Adjust file_path for use in Jupyter/Django
        contract_source_code = file.read()

    # Compile & Store Compiled source code
    

    compiled_sol = compile_source(contract_source_code,  solc_version="0.6.2")
  
    # Extract full interface as dict from compiled contract
    contract_interface = compiled_sol['<stdin>:'+interface]

    # Extract abi and bytecode
    abi = contract_interface['abi']
    bytecode = contract_interface['bin']
    
    # Create dictionary with interface
    d = dict()
    d['abi']      = abi
    d['bin'] = bytecode
    d['full_interface'] = contract_interface
    return(d)

def upload_data_consent(consent_obj, estimate):
    from web3 import Web3
    restrictions = consent_obj.restrictions
    user = consent_obj.user
    contract_address = consent_obj.contract_address
    noRestrictions = restrictions.no_restrictions
    openToGeneralResearchAndClinicalCare = restrictions.open_to_general_research_and_clinical_care
    openToHMBResearch = restrictions.open_to_HMB_research
    openToPopulationAndAncestryResearch = restrictions.open_to_population_and_ancestry_research
    openToDiseaseSpecific = restrictions.open_to_disease_specific

    d = compile_and_extract_interface_Consent()
    abi = d["abi"]

    user_address = user.ethereum_public_key
    private_key = user.ethereum_private_key
    contract_instance = w3.eth.contract(address=contract_address, abi=abi)
    user = w3.eth.account.privateKeyToAccount(private_key)

    nonce = w3.eth.getTransactionCount(user_address)
    txn_dict = {
        'from': user_address,
        'chainId': CHAIN_ID,
        'gasPrice': w3.toWei('20', 'gwei'),
        'nonce': nonce,
        }
    gas = contract_instance.functions.UploadDataPrimaryCategory(user_address, noRestrictions,openToGeneralResearchAndClinicalCare,openToHMBResearch,openToPopulationAndAncestryResearch,openToDiseaseSpecific).estimateGas(txn_dict)
    if estimate:
        return gas
    contract_txn = contract_instance.functions.UploadDataPrimaryCategory(user_address, noRestrictions,openToGeneralResearchAndClinicalCare,openToHMBResearch,openToPopulationAndAncestryResearch,openToDiseaseSpecific).buildTransaction(txn_dict)
    
    return sign_and_send(contract_txn, private_key, "upload consent statements to ConsentContract")


def give_research_purpose(consentContract, rp, user, estimate):
    from web3 import Web3
    contract_address = consentContract.contract_address
  

    d = compile_and_extract_interface_Consent()
    abi = d["abi"]

    user_address = user.ethereum_public_key
    private_key = user.ethereum_private_key
    contract_instance = w3.eth.contract(address=contract_address, abi=abi)
    user = w3.eth.account.privateKeyToAccount(private_key)
    nonce = w3.eth.getTransactionCount(user_address)
    txn_dict = {
        'from': user_address,
        'chainId': CHAIN_ID,
        'gasPrice': w3.toWei('20', 'gwei'),
        'nonce': nonce,
        }
    gas = contract_instance.functions.giveResearchPurpose(user_address, rp.use_for_methods_development, rp.use_for_reference_or_control_material, rp.use_for_populations_research, rp.use_for_ancestry_research, rp.use_for_HMB_research).estimateGas()

    txn_dict["gas"]=gas

    if estimate:
        return gas
        
    contract_txn = contract_instance.functions.giveResearchPurpose(user_address, rp.use_for_methods_development, rp.use_for_reference_or_control_material, rp.use_for_populations_research, rp.use_for_ancestry_research, rp.use_for_HMB_research).buildTransaction(txn_dict)
    return sign_and_send(contract_txn, private_key, "setting research purpuse in the consent contract")



def set_registry_address(datacontract, registry_address ,estimate):
    from web3 import Web3
    d = compile_and_extract_interface_Main()
    abi = d["abi"]
    contract_address = datacontract.contract_address

    user = datacontract.user
    user_address = user.ethereum_public_key
    private_key = user.ethereum_private_key
    contract_instance = w3.eth.contract(address=contract_address, abi=abi)
    user = w3.eth.account.privateKeyToAccount(private_key)
    nonce = w3.eth.getTransactionCount(user_address)
    txn_dict = {
        'from': user_address,
        'chainId': CHAIN_ID,
        'gasPrice': w3.toWei('20', 'gwei'),
        'nonce': nonce,
        }
    
    gas = contract_instance.functions.setRegistryAddress(registry_address).estimateGas(txn_dict)
    txn_dict["gas"]=gas

    if estimate:
        return gas
    
    contract_txn =  contract_instance.functions.setRegistryAddress(registry_address).buildTransaction(txn_dict)
    return sign_and_send(contract_txn, private_key, "setting registry address in Dataset contract" )

def is_registered(luceregistry, user, usertype):
    from web3 import Web3
    d = compile_and_extract_interface_Registry()
    abi = d["abi"]
    contract_address = luceregistry.contract_address        
    user_address = user.ethereum_public_key
    private_key = user.ethereum_private_key
    contract_instance = w3.eth.contract(address=contract_address, abi=abi)
    user = w3.eth.account.privateKeyToAccount(private_key)
    nonce = w3.eth.getTransactionCount(user_address)
    txn_dict = {
        'from': user_address,
        'chainId': CHAIN_ID,
        'gasPrice': w3.toWei('20', 'gwei'),
        'nonce': nonce,
        }
    if usertype == "requester":
        isRegistered = contract_instance.functions.checkUser(user_address).call()#returns a int (user exist if int != 0)
    else:
        isRegistered = contract_instance.functions.checkProvider(user_address).call()#returns a boolean

    return isRegistered


def set_consent_address(datacontract, consent_address ,estimate):
    from web3 import Web3
    d = compile_and_extract_interface_Main()
    abi = d["abi"]
    contract_address = datacontract.contract_address

    user = datacontract.user
    user_address = user.ethereum_public_key
    private_key = user.ethereum_private_key
    contract_instance = w3.eth.contract(address=contract_address, abi=abi)
    user = w3.eth.account.privateKeyToAccount(private_key)
    nonce = w3.eth.getTransactionCount(user_address)
    txn_dict = {
        'from': user_address,
        'chainId': CHAIN_ID,
        'gasPrice': w3.toWei('20', 'gwei'),
        'nonce': nonce,
        }
    
    gas = contract_instance.functions.setConsentAddress(consent_address).estimateGas(txn_dict)
    txn_dict["gas"]=gas

    if estimate:
        return gas
    
    contract_txn =  contract_instance.functions.setConsentAddress(consent_address).buildTransaction(txn_dict)
    return sign_and_send(contract_txn, private_key, "setting consent address in Dataset contract" )

def register_provider(registry, user, estimate):
    d = compile_and_extract_interface_Registry()
    abi = d["abi"]
    contract_address = registry.contract_address
    user = user
    user_address = user.ethereum_public_key
    private_key = user.ethereum_private_key
    contract_instance = w3.eth.contract(address=contract_address, abi=abi)
    user = w3.eth.account.privateKeyToAccount(private_key)
    nonce = w3.eth.getTransactionCount(user_address)

    txn_dict = {
        'from': user_address,
        'chainId': CHAIN_ID,
        'gasPrice': w3.toWei('20', 'gwei'),
        'nonce': nonce,
        }
        
    gas = contract_instance.functions.newDataProvider(user_address).estimateGas()
    txn_dict["gas"]=gas

    if estimate:
        return gas
    
    contract_txn =  contract_instance.functions.newDataProvider(user_address).buildTransaction(txn_dict)
    return sign_and_send(contract_txn,private_key, "registering dataprovider in the LuceRegistry contract" )

def register_requester(registry, user, license, estimate):
    d = compile_and_extract_interface_Registry()
    abi = d["abi"]
    contract_address = registry.contract_address
    user = user
    user_address = user.ethereum_public_key
    private_key = user.ethereum_private_key
    contract_instance = w3.eth.contract(address=contract_address, abi=abi)
    user = w3.eth.account.privateKeyToAccount(private_key)
    nonce = w3.eth.getTransactionCount(user_address)

    txn_dict = {
        'from': user_address,
        'chainId': CHAIN_ID,
        'gasPrice': w3.toWei('20', 'gwei'),
        'nonce': nonce,
        }
        
    gas = contract_instance.functions.registerNewUser(user_address, license).estimateGas()
    txn_dict["gas"]=gas

    if estimate:
        return gas
    
    contract_txn =  contract_instance.functions.registerNewUser(user_address,1).buildTransaction(txn_dict)
    return sign_and_send(contract_txn, private_key, "registering data requester in LuceRegistry contract")

def publish_dataset(datacontract, user, link, estimate):

    description = datacontract.description
    licence = datacontract.licence
    d = compile_and_extract_interface_Main()
    abi = d["abi"]
    contract_address = datacontract.contract_address
    user = user
    user_address = user.ethereum_public_key
    private_key = user.ethereum_private_key
    contract_instance = w3.eth.contract(address=contract_address, abi=abi)
    user = w3.eth.account.privateKeyToAccount(private_key)
    nonce = w3.eth.getTransactionCount(user_address)

    txn_dict = {
        'from': user_address,
        'chainId': CHAIN_ID,
        'gasPrice': w3.toWei('20', 'gwei'),
        'nonce': nonce,
        }
        
    gas = 650432#contract_instance.functions.publishData(description, link, licence).estimateGas(txn_dict)
    txn_dict["gas"]=gas

    if estimate:
        return gas
    
    contract_txn =  contract_instance.functions.publishData(description, link, licence).buildTransaction(txn_dict)
    return sign_and_send(contract_txn, private_key, "calling publishData function in Dataset Contract")

def get_link(datacontract, user, estimate):
    d = compile_and_extract_interface_Main()
    abi = d["abi"]
    contract_address = datacontract.contract_address
    
    user_address = user.ethereum_public_key
    private_key = user.ethereum_private_key
    contract_instance = w3.eth.contract(address=contract_address, abi=abi)
    user = w3.eth.account.privateKeyToAccount(private_key)
    nonce = w3.eth.getTransactionCount(user_address)

    txn_dict = {
        'from': user_address,
        'chainId': CHAIN_ID,
        'nonce': nonce,
        }

    
    contract_txn =  contract_instance.functions.getLink().call(txn_dict)
    return contract_txn


def add_data_requester(datacontract, access_time, purpose_code, user, estimate):
    d = compile_and_extract_interface_Main()
    abi = d["abi"]
    contract_address = datacontract.contract_address
    user_address = user.ethereum_public_key
    private_key = user.ethereum_private_key
    contract_instance = w3.eth.contract(address=contract_address, abi=abi)
    user = w3.eth.account.privateKeyToAccount(private_key)
    nonce = w3.eth.getTransactionCount(user_address)

    txn_dict = {
        'from': user_address,
        'chainId': CHAIN_ID,
        'gasPrice': w3.toWei('20', 'gwei'),
        'nonce': nonce,
        }
    

    cost =  contract_instance.functions.expectedCosts().call()
    txn_dict['value'] = cost
  
    gas = contract_instance.functions.addDataRequester(1,access_time).estimateGas(txn_dict)
    txn_dict["gas"]=gas

    if estimate:
        return gas


    contract_txn =  contract_instance.functions.addDataRequester(1, access_time).buildTransaction(txn_dict)
    tx = sign_and_send(contract_txn, private_key, "add data requester to the LuceMain contract")
    return tx

def receipt_to_dict(tx_receipt, name):
    receipt = {}
    receipt["blockHash"] = tx_receipt.blockHash.hex()
    receipt["blockNumber"] = tx_receipt.blockNumber
    receipt["contractAddress"] = tx_receipt.contractAddress
    receipt["cumulativeGasUsed"] = tx_receipt.cumulativeGasUsed
    receipt["effectiveGasPrice"] = w3.toInt(hexstr = tx_receipt.effectiveGasPrice)
    receipt["from"] = tx_receipt["from"]
    receipt["gasUsed"] = tx_receipt.gasUsed
    #receipt["logs"] = tx_receipt.logs
    receipt["logsBloom"] = tx_receipt.logsBloom.hex()
    receipt["status"] = tx_receipt.status
    receipt["to"] = tx_receipt.to
    receipt["transactionHash"] = tx_receipt.transactionHash.hex()
    receipt["transactionIndex"] = tx_receipt.transactionIndex
    receipt["type"] = tx_receipt.type
    receipt["fees"] =  receipt["effectiveGasPrice"] * receipt["gasUsed"]
    receipt["transaction name"] = name

    return receipt

def sign_and_send(contract_txn, private_key, name):
    try:

        signed_txn = w3.eth.account.signTransaction(contract_txn, private_key)
        tx_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        transaction = receipt_to_dict(tx_receipt, name)
    except ValueError as e:
        if DEBUG:
            print()
            print(e)
        return [e,name] 
    if DEBUG:
        print("======================================================")
        print(transaction)
    return transaction



"""
OLD CODE I KEEP FOR REFERENCES 


# Not used in Django Frontend anymore - kept for testing and reference
def create_wallet_old():
    print("This message comes from within my custom script")
    
    class EthAccount():
        address = None
        pkey = None

    def create_wallet():
        eth_account = EthAccount()
        eth_account_raw = w3.eth.account.create()
        eth_account.address = eth_account_raw.address
        eth_account.pkey = eth_account_raw.privateKey
        return (eth_account)

    eth_account = create_wallet()

    # Extract default accounts created by ganache
    accounts = w3.eth.accounts

    # Instantiate faucet object
    faucet = EthAccount()

    

    def send_ether(amount_in_ether, recipient_address, sender_address = faucet.address, sender_pkey=faucet.pkey):
        amount_in_wei = w3.toWei(amount_in_ether,'ether')

        # How many transactions have been made by wallet?
        # This is required and prevents double-spending.
        # Different from nonce in block mining.
        nonce = w3.eth.getTransactionCount(sender_address)
        
        # Specify transcation dictionary
        txn_dict = {
                'to': recipient_address,
                'value': amount_in_wei,
                'gas': 2000000,
                'gasPrice': w3.toWei('1', 'wei'),
                'nonce': nonce,
                'chainId': CHAIN_ID
        }
        
        # Sign transaction
        signed_txn = w3.eth.account.signTransaction(txn_dict, sender_pkey)

        # Send transaction & store transaction hash
        txn_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)

        # Check if transaction was added to blockchain
        # time.sleep(0.5)
        txn_receipt = w3.eth.getTransactionReceipt(txn_hash)
        return txn_hash

    # Send ether and store transaction hash
    txn_hash = send_ether(1.5,eth_account.address)

    # Show balance
    print("The balance of the new account is:\n")
    print(w3.eth.getBalance(eth_account.address))

    import os
 
    dirpath = os.getcwd()
    print("current directory is : " + dirpath)
    foldername = os.path.basename(dirpath)
    print("Directory name is : " + foldername)



def deploy_contract_with_data(user, description, license, link=""):
    from solcx import compile_source
    from web3 import Web3
    
    # Read in LUCE contract code
    with open(SOLIDITY_CONTRACT_FILE, 'r') as file:
        contract_source_code = file.read()
        
    # Compile & Store Compiled source code
    compiled_sol = compile_source(contract_source_code)

    # Extract full interface as dict from compiled contract
    contract_interface = compiled_sol['<stdin>:Dataset']

    # Extract abi and bytecode
    abi = contract_interface['abi']
    bytecode = contract_interface['bin']
    
    # Establish web3 connection

    # Obtin user
    current_user = user
    
    # Set sender
    w3.eth.defaultAccount = current_user.ethereum_public_key

    # Create contract blueprint
    Luce = w3.eth.contract(abi=abi, bytecode=bytecode)

    # Submit the transaction that deploys the contract
    tx_hash = Luce.constructor().transact()
    
    # Wait for the transaction to be mined, and get the transaction receipt
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    
    # Obtain address of freshly deployed contract
    contract_address = tx_receipt.contractAddress
    
    # Create python instance of deployed contract
    luce = w3.eth.contract(
    address=contract_address,
    abi=contract_interface['abi'],
    )
    
    # Store dataset information in contract
    tx_hash = luce.functions.publishData(description, link, license).transact()
    
    return contract_address

#### Initial Implementations
# These implementations make use of the Ganache pre-funded
# accounts. This is conveninent but doesn't scale well.
# To smoothen the later transition to a hosted node like Infura
# and using the official Ethereum testnet it it is preferable
# to have full control over the accounts.

def assign_address(user):
    # Establish web3 connection
    accounts = w3.eth.accounts
    # Obtain user model
    from django.contrib.auth import get_user_model
    User = get_user_model()
    # Obtain user count
    # The user count is used as a 'global counter'
    # to ensure each new user that registers is assigned
    # a new one of the pre-generated ganache acounts
    # I use this workaround as a proxy to track the
    # 'global state' of how many accounts are already
    # asigned.
    user_count = len(User.objects.all())
    idx = user_count-1
    # Assign web3 account to user
    current_user = user
    current_user.ethereum_public_key = accounts[idx]
    current_user.save()
    # Return user with address associated
    return current_user
	


"""


