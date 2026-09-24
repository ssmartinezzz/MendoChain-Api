# MendoChain API

Backend for MendoChain, a wine traceability platform that records each bottle's journey through the supply chain on the Algorand blockchain.

Built with Django REST Framework, JWT authentication and the Algorand Python SDK. The end-to-end suite lives in [MendoChainAutomatedTests](https://github.com/ssmartinezzz/MendoChainAutomatedTests).

## Features

- Wine and supply-chain entities exposed through a REST API with filtering and pagination
- JWT authentication with `djangorestframework-simplejwt`
- Traceability events written as Algorand TestNet transactions

## Getting started

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your own values
python manage.py migrate
python manage.py runserver
```

### Hyperledger Fabric network (optional)

`mendochain-network/crypto-config.yaml` describes the test network topology. Generate its certificates and keys locally with:

```bash
cryptogen generate --config=mendochain-network/crypto-config.yaml --output=mendochain-network/crypto-config
```

Generated key material is ignored by git and must never be committed.
