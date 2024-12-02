from tinkoff.invest.sandbox.client import SandboxClient
import pprint

from TOKEN import TOKEN
import os

from tinkoff.invest import Client

def main():
    with Client(TOKEN) as client:
        pprint.pprint(client.users.get_accounts())


if __name__ == "__main__":
    main()
