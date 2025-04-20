import streamlit as st
import pytesseract
from PIL import Image
import json
import random
import string
import os
from web3 import Web3
import streamlit.components.v1 as components
from eth_account import Account
import secrets


# Page setup
st.set_page_config(
    page_title="Carbon Footprint from Receipts", 
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed"
    )
# Load carbon data
with open('carbon_data.json', 'r') as f:
    carbon_data = json.load(f)

# Initialize Web3
def init_web3():
    try:
        # Connect to Mega testnet
        w3 = Web3(Web3.HTTPProvider('https://carrot.megaeth.com/rpc'))
        return w3 if w3.is_connected() else None
    except Exception as e:
        st.error(f"Failed to connect to network: {str(e)}")
        return None

def connect_wallet(address=None):
    if address:
        # Validate the address format
        if Web3.is_address(address):
            st.session_state.wallet_address = address
            st.session_state.wallet_connected = True
            return address
        else:
            st.error("Invalid wallet address format")
            return None
    else:
        if 'private_key' not in st.session_state:
            private_key = '0x' + secrets.token_hex(32)
            st.session_state.private_key = private_key
            account = Account.from_key(private_key)
            st.session_state.wallet_address = account.address
            return account.address
        else:
            account = Account.from_key(st.session_state.private_key)
            return account.address

def get_balance(address):
    w3 = init_web3()
    if w3:
        try:
            balance = w3.eth.get_balance(address)
            return w3.from_wei(balance, 'ether')
        except Exception as e:
            st.error(f"Failed to get balance: {str(e)}")
            return 0
    return 0

def calculate_rewards(total_footprint):
    """Calculate rewards based on carbon footprint"""
    max_footprint = 100
    base_reward = 10
    
    if total_footprint <= 0:
        return base_reward
    elif total_footprint >= max_footprint:
        return 0
    else:
        return base_reward * (1 - (total_footprint / max_footprint))

def search_carbon_data(query):
    """Search for items in carbon data"""
    results = []
    query = query.lower()
    for item in carbon_data:
        if query in item["category"].lower():
            results.append(item)
    return results

def main():
    st.title("Carbon Footprint Calculator & Rewards")
    
    # Sidebar
    st.sidebar.title("Carbon Database Search")
    
    # Search functionality
    search_query = st.sidebar.text_input("Search for items", placeholder="e.g., beef, milk, laptop")
    
    if search_query:
        results = search_carbon_data(search_query)
        if results:
            st.sidebar.subheader("Search Results")
            for item in results:
                with st.sidebar.expander(f"{item['category']}"):
                    st.markdown(f"""
                    **Carbon Footprint:** {item['footprint']} kg CO₂
                    
                    **Alternative Suggestion:** {item['alt']}
                    
                    **Impact Level:**
                    """)
                    if item['footprint'] < 2:
                        st.success("Low Impact")
                    elif item['footprint'] < 10:
                        st.warning("Medium Impact")
                    else:
                        st.error("High Impact")
        else:
            st.sidebar.info("No items found. Try a different search term.")
    
    # Wallet Connection Section in Sidebar
    st.sidebar.markdown("---")
    st.sidebar.title("Wallet Connection")
    
    # Add wallet address input
    wallet_address = st.sidebar.text_input("Enter Wallet Address (Optional)", 
                                         placeholder="0x...")
    
    if st.sidebar.button("Connect Wallet"):
        if wallet_address:
            # Connect with provided address
            address = connect_wallet(wallet_address)
        else:
            # Generate new wallet
            address = connect_wallet()
            
        if address:
            st.session_state.wallet_connected = True
            st.session_state.wallet_address = address
            st.session_state.wallet_balance = get_balance(address)
    
    # Display wallet info if connected
    if st.session_state.get('wallet_connected', False):
        st.sidebar.success(f"Connected: {st.session_state.wallet_address[:6]}...{st.session_state.wallet_address[-4:]}")
        st.sidebar.info(f"Balance: {st.session_state.wallet_balance:.4f} MegaETH")
        
        # Add network info
        with st.sidebar.expander("Network Information"):
            st.markdown("""
            **Mega Testnet Details:**
            - Network Name: Mega Testnet
            - RPC URL: carrot.megaeth.com/rpc
            - Chain ID: 6342
            - Currency Symbol: MegaETH
            - Block Explorer: megaexplorer.xyz
            """)
            
        # Add refresh balance button
        if st.sidebar.button("Refresh Balance"):
            st.session_state.wallet_balance = get_balance(st.session_state.wallet_address)
            st.rerun()
    else:
        st.sidebar.warning("Wallet not connected")
    
    # Initialize footprint variables
    transport_footprint = 0
    food_footprint = 0
    
    # Receipt Upload Section
    st.header("Receipt Analysis")
    uploaded_file = st.file_uploader("Upload your receipt", type=["png", "jpg", "jpeg"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Receipt", use_column_width=True)
        
        with st.spinner("Analyzing receipt..."):
            text = pytesseract.image_to_string(image)
            
        st.subheader("Extracted Items")
        items = [line.strip() for line in text.split("\n") if line.strip()]
        
        # Calculate food footprint
        for item in items:
            for entry in carbon_data:
                if entry["category"].lower() in item.lower():
                    food_footprint += entry["footprint"]
                    col1, col2 = st.columns([3, 2])
                    with col1:
                        st.markdown(f"- {entry['category']}: {entry['footprint']} kg CO₂")
                    with col2:
                        st.info(f"Tip: {entry['alt']}")
                        
        if food_footprint > 0:
            st.markdown("---")
            st.subheader("Food Carbon Footprint Summary")
            st.metric("Total Food Footprint", f"{food_footprint:.2f} kg CO₂")
            
            # Add impact level indicator
            if food_footprint < 10:
                st.success("Low Impact - Great job!")
            elif food_footprint < 30:
                st.warning("Medium Impact - Room for improvement")
            else:
                st.error("High Impact - Consider eco-friendly alternatives")
    
    # Transportation Section
    st.header("Transportation")
    with st.expander("Add Transportation Impact"):
        vehicle_type = st.selectbox("Vehicle Type", 
            ["Petrol Car", "Diesel Car", "Bus", "Train", "Electric Car", "Domestic Flight"])
        distance = st.number_input("Distance (km)", min_value=0.0, step=0.1)
        
        if st.button("Calculate"):
            emission_factors = {
                "Petrol Car": 0.192,
                "Diesel Car": 0.171,
                "Bus": 0.105,
                "Train": 0.041,
                "Electric Car": 0.05,
                "Domestic Flight": 0.255
            }
            transport_footprint = round(distance * emission_factors[vehicle_type], 2)
            st.success(f"Transportation footprint: {transport_footprint} kg CO₂")
    
    # Total Impact & Rewards
    total_footprint = transport_footprint + food_footprint
    reward_amount = calculate_rewards(total_footprint)
    
    st.markdown("---")
    st.header("Total Impact & Rewards")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Carbon Footprint", f"{total_footprint:.2f} kg CO₂")
    with col2:
        st.metric("Available Rewards", f"{reward_amount:.2f} MegaETH")
    
    # Claim Rewards
    if total_footprint > 0 and reward_amount > 0:
        st.markdown("---")
        st.subheader("Claim Rewards")
        
        if st.session_state.get('wallet_connected', False):
            if st.button("Claim MegaETH Rewards"):
                w3 = init_web3()
                if w3:
                    try:
                        # Contract interaction code here
                        contract_address = "0x333553184a2f904aA6Ed1f5ffa84F0A9255a8216"
                        contract_abi = [
                            {
                                "inputs": [
                                    {
                                        "internalType": "address",
                                        "name": "user",
                                        "type": "address"
                                    },
                                    {
                                        "internalType": "uint256",
                                        "name": "amount",
                                        "type": "uint256"
                                    }
                                ],
                                "name": "reward",
                                "outputs": [],
                                "stateMutability": "nonpayable",
                                "type": "function"
                            }
                        ]
                        
                        contract = w3.eth.contract(address=contract_address, abi=contract_abi)
                        account = Account.from_key(st.session_state.private_key)
                        
                        # Build transaction
                        nonce = w3.eth.get_transaction_count(account.address)
                        reward_wei = w3.to_wei(reward_amount, 'ether')
                        
                        transaction = contract.functions.reward(
                            account.address,
                            reward_wei
                        ).build_transaction({
                            'chainId': 6342,
                            'gas': 100000,
                            'gasPrice': w3.eth.gas_price,
                            'nonce': nonce,
                        })
                        
                        # Sign and send transaction
                        signed_txn = w3.eth.account.sign_transaction(transaction, st.session_state.private_key)
                        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                        
                        # Wait for transaction receipt
                        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
                        
                        if receipt['status'] == 1:
                            st.success(f"""
                            🎉 Rewards claimed successfully!
                            - Amount: {reward_amount} MegaETH
                            - Transaction Hash: {receipt['transactionHash'].hex()}
                            """)
                            st.markdown(f"[View on Explorer](https://megaexplorer.xyz/tx/{receipt['transactionHash'].hex()})")
                        else:
                            st.error("Transaction failed")
                            
                    except Exception as e:
                        st.error(f"Failed to claim rewards: {str(e)}")
        else:
            st.warning("Please connect your wallet to claim rewards")
    
    # Footer
    st.markdown("---")
    st.markdown("Created by **The Cryptic Crew**")

if __name__ == "__main__":
    main() 