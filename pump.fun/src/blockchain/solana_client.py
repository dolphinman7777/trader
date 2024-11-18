from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
import os
from base58 import b58decode
import json
import aiohttp

class SolanaClient:
    def __init__(self):
        # Initialize Solana client (use devnet for testing)
        self.endpoint = os.getenv('SOLANA_RPC_ENDPOINT', 'https://api.mainnet-beta.solana.com')
        self.client = AsyncClient(self.endpoint)
        
        # Load wallet from environment
        private_key = b58decode(os.getenv('SOLANA_PRIVATE_KEY'))
        self.wallet = Keypair.from_bytes(private_key)
        
        # Multiple price API endpoints for redundancy
        self.price_apis = {
            'jupiter': "https://price.jup.ag/v4/price",
            'birdeye': "https://public-api.birdeye.so/public/price",
            'coingecko': "https://api.coingecko.com/api/v3/simple/price"
        }

    async def get_token_price(self, token_address: str) -> float:
        """Try multiple price sources until we get a valid price"""
        try:
            # Try Jupiter first
            price = await self._get_jupiter_price(token_address)
            if price:
                return price
                
            # Try Birdeye as backup
            price = await self._get_birdeye_price(token_address)
            if price:
                return price
                
            # Try CoinGecko as last resort (only works for major tokens)
            if token_address == "So11111111111111111111111111111111111111112":  # SOL
                price = await self._get_coingecko_price("solana")
                if price:
                    return price
            
            return None
                        
        except Exception as e:
            print(f"Error getting token price: {e}")
            return None

    async def _get_jupiter_price(self, token_address: str) -> float:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.price_apis['jupiter'],
                    params={
                        "ids": token_address,
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data.get('data', {}).get(token_address, {}).get('price', 0))
            return None
        except Exception as e:
            print(f"Jupiter price error: {e}")
            return None

    async def _get_birdeye_price(self, token_address: str) -> float:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.price_apis['birdeye']}/{token_address}"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data.get('data', {}).get('value', 0))
            return None
        except Exception as e:
            print(f"Birdeye price error: {e}")
            return None

    async def _get_coingecko_price(self, token_id: str) -> float:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.price_apis['coingecko'],
                    params={
                        "ids": token_id,
                        "vs_currencies": "usd"
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data.get(token_id, {}).get('usd', 0))
            return None
        except Exception as e:
            print(f"CoinGecko price error: {e}")
            return None

    async def execute_swap(self, token_in: str, token_out: str, amount: float) -> bool:
        try:
            # Get best route from Jupiter
            route = await self._get_best_route(token_in, token_out, amount)
            
            # Build and send transaction
            transaction = await self._build_swap_transaction(route)
            
            # Sign and send transaction
            result = await self._send_transaction(transaction)
            
            return result
        except Exception as e:
            print(f"Error executing swap: {e}")
            return False

    async def _get_best_route(self, token_in: str, token_out: str, amount: float):
        try:
            # Convert amount to proper units (lamports for SOL)
            input_amount = int(amount * 1e9)  # SOL has 9 decimals
            
            params = {
                "inputMint": token_in,
                "outputMint": token_out,
                "amount": str(input_amount),
                "slippageBps": 50,  # 0.5% slippage
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.jupiter_api}/quote", params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Error getting route: {await response.text()}")
                        return None
                        
        except Exception as e:
            print(f"Error in get_best_route: {e}")
            return None

    async def _build_swap_transaction(self, route):
        if not route:
            return None
            
        try:
            async with aiohttp.ClientSession() as session:
                # Get serialized transaction
                async with session.post(
                    f"{self.jupiter_api}/swap",
                    json={
                        "route": route,
                        "userPublicKey": str(self.wallet.pubkey())
                    }
                ) as response:
                    if response.status == 200:
                        swap_data = await response.json()
                        # Convert serialized transaction to Transaction object
                        return Transaction.deserialize(bytes(swap_data['swapTransaction']))
                    else:
                        print(f"Error building swap: {await response.text()}")
                        return None
                        
        except Exception as e:
            print(f"Error in build_swap_transaction: {e}")
            return None

    async def _send_transaction(self, transaction: Transaction) -> bool:
        try:
            # Sign and send transaction
            result = await self.client.send_transaction(
                transaction,
                self.wallet,
                opts={"skip_preflight": True}
            )
            return result.value is not None
        except Exception as e:
            print(f"Error sending transaction: {e}")
            return False 