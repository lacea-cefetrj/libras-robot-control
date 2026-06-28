import os
from ament_index_python.packages import get_package_share_directory

def obter_caminho_modelo(nome_arquivo: str = "best.pt") -> str:
    pkg_dir = get_package_share_directory("libras_modelo_yolo")
    caminho = os.path.join(pkg_dir, "models", nome_arquivo)
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Modelo não encontrado em: {caminho}")
    return caminho
