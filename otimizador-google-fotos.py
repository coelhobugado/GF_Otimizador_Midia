"""
Otimizador de Mídia - Google Fotos
-----------------------------------
Este script otimiza fotos e vídeos baixados do Google Fotos,
reduzindo o tamanho dos arquivos enquanto mantém a qualidade visual.

Requisitos:
- Python 3.6+
- Pillow (PIL Fork)
- ffmpeg-python
- tqdm (para barra de progresso)
"""

import os
import sys
import json
import shutil
import time
import logging
import argparse
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union

try:
    from PIL import Image, ImageFile
    import ffmpeg
    from tqdm import tqdm
except ImportError:
    print("Erro: Dependências não instaladas.")
    print("Execute: pip install pillow ffmpeg-python tqdm")
    sys.exit(1)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("otimizacao_midia.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configurações padrão
CONFIGURACOES = {
    "imagens": {
        "qualidade_jpg": 85,
        "qualidade_png": 9,
        "resoluções_max": None,
        "converter_png_para_jpg": False,
        "ignorar_pequenas": True,
        "tamanho_minimo_kb": 100,
    },
    "videos": {
        "crf": 23,
        "codec": "libx264",
        "preset": "medium",
        "audio_bitrate": "128k",
        "escala_max": None,
        "ignorar_pequenos": True,
        "tamanho_minimo_mb": 5,
    },
    "geral": {
        "processos": os.cpu_count(),
        "manter_originais": True,
        "pasta_backup": None,
        "extensoes_imagem": [".jpg", ".jpeg", ".png", ".webp"],
        "extensoes_video": [".mp4", ".mov", ".avi", ".mkv"],
    }
}

class OtimizadorMidia:
    def __init__(self, pasta_entrada: str, pasta_saida: Optional[str] = None, 
                 config: Optional[Dict] = None):
        self.pasta_entrada = Path(pasta_entrada).absolute()
        self.pasta_saida = Path(pasta_saida).absolute() if pasta_saida else self.pasta_entrada / "otimizados"
        self.config = CONFIGURACOES.copy()
        
        if config:
            for categoria, valores in config.items():
                if categoria in self.config:
                    self.config[categoria].update(valores)
        
        self.pasta_backup = None
        if self.config["geral"]["manter_originais"]:
            self.pasta_backup = (Path(self.config["geral"]["pasta_backup"]).absolute() 
                               if self.config["geral"]["pasta_backup"] 
                               else self.pasta_entrada / "originais")
        
        self.pasta_saida.mkdir(exist_ok=True, parents=True)
        if self.pasta_backup:
            self.pasta_backup.mkdir(exist_ok=True, parents=True)
        
        self.estatisticas = {
            "total_arquivos": 0,
            "total_imagens": 0,
            "total_videos": 0,
            "imagens_otimizadas": 0,
            "videos_otimizados": 0,
            "arquivos_ignorados": 0,
            "erros": 0,
            "espaco_economizado": 0,
            "tamanho_original": 0,
            "tamanho_final": 0,
            "inicio": time.time(),
            "fim": 0
        }
        
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        self.metadata_cache = {}
    
    def ler_metadata_json(self, caminho_arquivo: Path) -> Optional[Dict]:
        try:
            json_path = Path(f"{caminho_arquivo}.json")
            metadata_path = Path(f"{caminho_arquivo}.supplemental-metadata.json")
            
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return None
        except Exception as e:
            logger.warning(f"Erro ao ler metadata JSON para {caminho_arquivo.name}: {e}")
            return None
    
    def copiar_metadata_json(self, origem: Path, destino: Path) -> None:
        try:
            for ext in ['.json', '.supplemental-metadata.json']:
                json_origem = Path(f"{origem}{ext}")
                if json_origem.exists():
                    json_destino = Path(f"{destino}{ext}")
                    shutil.copy2(json_origem, json_destino)
        except Exception as e:
            logger.warning(f"Erro ao copiar metadata JSON: {e}")
    
    def procurar_arquivos(self) -> Tuple[List[Path], List[Path]]:
        logger.info(f"Analisando arquivos em: {self.pasta_entrada}")
        
        imagens = []
        videos = []
        
        for item in self.pasta_entrada.rglob("*"):
            if item.is_file():
                if item.suffix.lower().endswith(('.json', '.metadata')):
                    continue
                    
                ext = item.suffix.lower()
                if ext in [x.lower() for x in self.config["geral"]["extensoes_imagem"]]:
                    imagens.append(item)
                elif ext in [x.lower() for x in self.config["geral"]["extensoes_video"]]:
                    videos.append(item)
        
        self.estatisticas.update({
            "total_imagens": len(imagens),
            "total_videos": len(videos),
            "total_arquivos": len(imagens) + len(videos)
        })
        
        logger.info(f"Encontrados: {len(imagens)} imagens e {len(videos)} vídeos")
        return imagens, videos
    
    def otimizar_imagem(self, caminho_imagem: Path) -> Optional[Path]:
        try:
            tamanho_original = caminho_imagem.stat().st_size
            
            if (self.config["imagens"]["ignorar_pequenas"] and 
                tamanho_original < self.config["imagens"]["tamanho_minimo_kb"] * 1024):
                logger.debug(f"Ignorando imagem pequena: {caminho_imagem.name}")
                self.estatisticas["arquivos_ignorados"] += 1
                return None
            
            metadata = self.ler_metadata_json(caminho_imagem)
            caminho_relativo = caminho_imagem.relative_to(self.pasta_entrada)
            caminho_saida = self.pasta_saida / caminho_relativo
            caminho_saida.parent.mkdir(exist_ok=True, parents=True)
            
            if self.pasta_backup:
                caminho_backup = self.pasta_backup / caminho_relativo
                caminho_backup.parent.mkdir(exist_ok=True, parents=True)
                shutil.copy2(caminho_imagem, caminho_backup)
                self.copiar_metadata_json(caminho_imagem, caminho_backup)
            
            with Image.open(caminho_imagem) as img:
                if self.config["imagens"]["resoluções_max"]:
                    max_width, max_height = self.config["imagens"]["resoluções_max"]
                    if img.width > max_width or img.height > max_height:
                        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                formato = caminho_imagem.suffix.lower()
                if formato in ['.jpg', '.jpeg']:
                    formato_saida = 'JPEG'
                    kwargs = {'quality': self.config["imagens"]["qualidade_jpg"], 
                            'optimize': True}
                elif formato == '.png':
                    if self.config["imagens"]["converter_png_para_jpg"]:
                        formato_saida = 'JPEG'
                        caminho_saida = caminho_saida.with_suffix('.jpg')
                        kwargs = {'quality': self.config["imagens"]["qualidade_jpg"], 
                                'optimize': True}
                    else:
                        formato_saida = 'PNG'
                        kwargs = {'optimize': True, 
                                'compress_level': self.config["imagens"]["qualidade_png"]}
                else:
                    formato_saida = 'JPEG'
                    caminho_saida = caminho_saida.with_suffix('.jpg')
                    kwargs = {'quality': self.config["imagens"]["qualidade_jpg"], 
                            'optimize': True}
                
                img.save(caminho_saida, formato_saida, **kwargs)
            
            self.copiar_metadata_json(caminho_imagem, caminho_saida)
            
            tamanho_novo = caminho_saida.stat().st_size
            economia = tamanho_original - tamanho_novo
            
            self.estatisticas.update({
                "tamanho_original": self.estatisticas["tamanho_original"] + tamanho_original,
                "tamanho_final": self.estatisticas["tamanho_final"] + tamanho_novo,
                "espaco_economizado": self.estatisticas["espaco_economizado"] + economia,
                "imagens_otimizadas": self.estatisticas["imagens_otimizadas"] + 1
            })
            
            return caminho_saida
            
        except Exception as e:
            logger.error(f"Erro ao otimizar imagem {caminho_imagem}: {e}")
            self.estatisticas["erros"] += 1
            return None
    
    def otimizar_video(self, caminho_video: Path) -> Optional[Path]:
        try:
            tamanho_original = caminho_video.stat().st_size
            
            if (self.config["videos"]["ignorar_pequenos"] and 
                tamanho_original < self.config["videos"]["tamanho_minimo_mb"] * 1024 * 1024):
                logger.debug(f"Ignorando vídeo pequeno: {caminho_video.name}")
                self.estatisticas["arquivos_ignorados"] += 1
                return None
            
            metadata = self.ler_metadata_json(caminho_video)
            caminho_relativo = caminho_video.relative_to(self.pasta_entrada)
            caminho_saida = self.pasta_saida / caminho_relativo
            caminho_saida.parent.mkdir(exist_ok=True, parents=True)
            
            if self.pasta_backup:
                caminho_backup = self.pasta_backup / caminho_relativo
                caminho_backup.parent.mkdir(exist_ok=True, parents=True)
                shutil.copy2(caminho_video, caminho_backup)
                self.copiar_metadata_json(caminho_video, caminho_backup)
            
            # Enhanced FFmpeg configuration
            stream = ffmpeg.input(str(caminho_video), err_detect='ignore_err')
            
            video_args = {
                'c:v': self.config["videos"]["codec"],
                'crf': self.config["videos"]["crf"],
                'preset': self.config["videos"]["preset"],
                'map_metadata': 0,
                'max_muxing_queue_size': 1024,
                'movflags': '+faststart'
            }
            
            if self.config["videos"]["escala_max"]:
                max_width, max_height = self.config["videos"]["escala_max"]
                video_args['vf'] = f'scale=w={max_width}:h={max_height}:force_original_aspect_ratio=decrease'
            
            audio_args = {
                'c:a': 'aac',
                'b:a': self.config["videos"]["audio_bitrate"],
                'strict': 'experimental',
                'ar': 48000
            }
            
            args = {**video_args, **audio_args}
            
            try:
                # Create temporary file path
                temp_output = caminho_saida.with_name(f"temp_{caminho_saida.name}")
                
                # First pass: process video
                ffmpeg.output(stream, str(temp_output), **args).run(
                    quiet=True,
                    overwrite_output=True,
                    capture_stderr=True
                )
                
                # Check if temporary file was created successfully
                if not temp_output.exists():
                    raise FileNotFoundError(f"Arquivo temporário não foi criado: {temp_output}")
                
                # Move temporary file to final destination
                if temp_output.exists():
                    if caminho_saida.exists():
                        caminho_saida.unlink()
                    temp_output.rename(caminho_saida)
                
            except ffmpeg.Error as e:
                logger.error(f"Erro FFmpeg: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}")
                if temp_output.exists():
                    temp_output.unlink()
                raise
            
            self.copiar_metadata_json(caminho_video, caminho_saida)
            
            tamanho_novo = caminho_saida.stat().st_size
            economia = tamanho_original - tamanho_novo
            
            self.estatisticas.update({
                "tamanho_original": self.estatisticas["tamanho_original"] + tamanho_original,
                "tamanho_final": self.estatisticas["tamanho_final"] + tamanho_novo,
                "espaco_economizado": self.estatisticas["espaco_economizado"] + economia,
                "videos_otimizados": self.estatisticas["videos_otimizados"] + 1
            })
            
            return caminho_saida
            
        except Exception as e:
            logger.error(f"Erro ao otimizar vídeo {caminho_video}: {e}")
            self.estatisticas["erros"] += 1
            return None
    
    def processar_todos(self) -> None:
        imagens, videos = self.procurar_arquivos()
        total = len(imagens) + len(videos)
        
        if total == 0:
            logger.warning("Nenhum arquivo de mídia encontrado para otimizar.")
            return
        
        logger.info(f"Iniciando otimização de {total} arquivos...")
        max_workers = self.config["geral"]["processos"]
        
        if imagens:
            logger.info(f"Otimizando {len(imagens)} imagens...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(tqdm(
                    executor.map(self.otimizar_imagem, imagens),
                    total=len(imagens),
                    desc="Otimizando imagens",
                    unit="img"
                ))
        
        if videos:
            logger.info(f"Otimizando {len(videos)} vídeos...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(tqdm(
                    executor.map(self.otimizar_video, videos),
                    total=len(videos),
                    desc="Otimizando vídeos",
                    unit="vid"
                ))
        
        self.estatisticas["fim"] = time.time()
        self.exibir_estatisticas()
    
    def exibir_estatisticas(self) -> None:
        """Exibe estatísticas da otimização."""
        tempo_total = self.estatisticas["fim"] - self.estatisticas["inicio"]
        espaco_economizado_mb = self.estatisticas["espaco_economizado"] / (1024 * 1024)
        tamanho_original_mb = self.estatisticas["tamanho_original"] / (1024 * 1024)
        tamanho_final_mb = self.estatisticas["tamanho_final"] / (1024 * 1024)
        
        if tamanho_original_mb > 0:
            porcentagem_reducao = (espaco_economizado_mb / tamanho_original_mb) * 100
        else:
            porcentagem_reducao = 0
            
        print("\n" + "="*50)
        print(f"ESTATÍSTICAS DE OTIMIZAÇÃO")
        print("="*50)
        print(f"Tempo de processamento: {tempo_total:.2f} segundos")
        print(f"Arquivos processados: {self.estatisticas['total_arquivos']}")
        print(f"  - Imagens otimizadas: {self.estatisticas['imagens_otimizadas']} de {self.estatisticas['total_imagens']}")
        print(f"  - Vídeos otimizados: {self.estatisticas['videos_otimizados']} de {self.estatisticas['total_videos']}")
        print(f"  - Arquivos ignorados: {self.estatisticas['arquivos_ignorados']}")
        print(f"  - Erros: {self.estatisticas['erros']}")
        print(f"Tamanho original: {tamanho_original_mb:.2f} MB")
        print(f"Tamanho final: {tamanho_final_mb:.2f} MB")
        print(f"Espaço economizado: {espaco_economizado_mb:.2f} MB ({porcentagem_reducao:.1f}%)")
        
        # Salvar relatório em arquivo
        relatorio = self.pasta_saida / f"relatorio_otimizacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(relatorio, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO DE OTIMIZAÇÃO DE MÍDIA\n")
            f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Pasta de entrada: {self.pasta_entrada}\n")
            f.write(f"Pasta de saída: {self.pasta_saida}\n")
            f.write("\n")
            f.write(f"Tempo de processamento: {tempo_total:.2f} segundos\n")
            f.write(f"Arquivos processados: {self.estatisticas['total_arquivos']}\n")
            f.write(f"  - Imagens otimizadas: {self.estatisticas['imagens_otimizadas']} de {self.estatisticas['total_imagens']}\n")
            f.write(f"  - Vídeos otimizados: {self.estatisticas['videos_otimizados']} de {self.estatisticas['total_videos']}\n")
            f.write(f"  - Arquivos ignorados: {self.estatisticas['arquivos_ignorados']}\n")
            f.write(f"  - Erros: {self.estatisticas['erros']}\n")
            f.write(f"Tamanho original: {tamanho_original_mb:.2f} MB\n")
            f.write(f"Tamanho final: {tamanho_final_mb:.2f} MB\n")
            f.write(f"Espaço economizado: {espaco_economizado_mb:.2f} MB ({porcentagem_reducao:.1f}%)\n")
        
        logger.info(f"Relatório salvo em: {relatorio}")
        print("-"*50)
        print(f"Processo concluído! Arquivos otimizados salvos em: {self.pasta_saida}")
        if self.pasta_backup:
            print(f"Arquivos originais preservados em: {self.pasta_backup}")


def main():
    """Função principal que analisa argumentos e inicia processamento."""
    parser = argparse.ArgumentParser(
        description="Otimizador de Fotos e Vídeos do Google Fotos",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("pasta_entrada", type=str, 
                        help="Pasta contendo as fotos e vídeos do Google Fotos")
    
    parser.add_argument("-o", "--pasta-saida", type=str, default=None,
                        help="Pasta para salvar os arquivos otimizados")
    
    parser.add_argument("-b", "--pasta-backup", type=str, default=None,
                        help="Pasta para backup dos arquivos originais")
    
    parser.add_argument("-j", "--qualidade-jpg", type=int, default=85,
                        help="Qualidade JPEG (1-100)")
    
    parser.add_argument("--converter-png", action="store_true",
                        help="Converter PNGs para JPG")
    
    parser.add_argument("--sem-backup", action="store_true",
                        help="Não fazer backup dos arquivos originais")
    
    parser.add_argument("-p", "--processos", type=int, default=os.cpu_count(),
                        help="Número de processos paralelos")
    
    parser.add_argument("--crf", type=int, default=23,
                        help="Fator de qualidade de vídeo (0-51, menor = melhor)")
    
    parser.add_argument("--preset", type=str, default="medium",
                        choices=["ultrafast", "superfast", "veryfast", "faster", 
                                 "fast", "medium", "slow", "slower", "veryslow"],
                        help="Preset de codificação de vídeo")
    
    args = parser.parse_args()
    
    # Configurações personalizadas
    config = {
        "imagens": {
            "qualidade_jpg": args.qualidade_jpg,
            "converter_png_para_jpg": args.converter_png,
        },
        "videos": {
            "crf": args.crf,
            "preset": args.preset,
        },
        "geral": {
            "processos": args.processos,
            "manter_originais": not args.sem_backup,
            "pasta_backup": args.pasta_backup,
        }
    }
    
    # Verificar se pasta de entrada existe
    if not os.path.exists(args.pasta_entrada):
        print(f"Erro: A pasta de entrada '{args.pasta_entrada}' não existe.")
        sys.exit(1)
    
    # Iniciar otimização
    otimizador = OtimizadorMidia(args.pasta_entrada, args.pasta_saida, config)
    otimizador.processar_todos()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcesso interrompido pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print(f"\nErro inesperado: {e}")
        logger.exception("Erro fatal no script principal")
        sys.exit(1)
