import boto3
import yaml
import json

BUCKET = 'safeteer-config'
BASE_KEY = 'base/config-global.yaml'

s3 = boto3.client('s3')


def carregar_yaml(key):
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    return yaml.safe_load(obj['Body'].read())


def salvar_yaml(key, data):
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=yaml.dump(data, sort_keys=False),
        ACL='bucket-owner-full-control'
    )


# 🧠 Merge normal para dicionários: adiciona apenas chaves que não existem
def merge_aditivamente(global_cfg, cliente_cfg):
    for k, v in global_cfg.items():
        if k not in cliente_cfg:
            cliente_cfg[k] = v
        elif isinstance(v, dict) and isinstance(cliente_cfg[k], dict):
            merge_aditivamente(v, cliente_cfg[k])
        elif isinstance(v, list) and k == "modulos":
            cliente_cfg[k] = merge_modulos(v, cliente_cfg[k])
    return cliente_cfg


# 🧠 Merge inteligente de módulos (lista de dicts por nome)
def merge_modulos(mods_global, mods_cliente):
    nomes_cliente = {m['nome']: m for m in mods_cliente}

    for mod_global in mods_global:
        nome = mod_global['nome']
        if nome not in nomes_cliente:
            mods_cliente.append(mod_global)  # Novo módulo: adiciona tudo
        else:
            mod_cliente = nomes_cliente[nome]
            merge_aditivamente(mod_global, mod_cliente)  # Merge só das partes novas
    return mods_cliente


def main():
    with open('canary_clients.json') as f:
        clientes = json.load(f)

    with open('config-global.yaml') as f:
        global_config = yaml.safe_load(f)

    for cliente in clientes:
        key = f"{cliente}/config.yaml"
        try:
            cliente_config = carregar_yaml(key)
        except s3.exceptions.NoSuchKey:
            print(f"{cliente} não tem config.yaml, pulando.")
            continue

        merged = merge_aditivamente(global_config, cliente_config)
        salvar_yaml(key, merged)
        print(f"Atualizado: {cliente}")


if __name__ == "__main__":
    main()
