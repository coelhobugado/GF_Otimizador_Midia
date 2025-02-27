# Otimizador de Mídia - Google Fotos

Este é um script Python que otimiza fotos e vídeos baixados do Google Fotos, reduzindo o tamanho dos arquivos enquanto mantém a qualidade visual. Ele é especialmente útil para quem deseja economizar espaço em disco após exportar suas mídias do Google Fotos.

---

## Funcionalidades

- **Otimização de Imagens**:
  - Reduz o tamanho de arquivos JPEG, PNG e WEBP.
  - Permite redimensionar imagens para uma resolução máxima configurável.
  - Converte PNG para JPEG (opcional).
  - Preserva metadados EXIF e arquivos JSON de metadados do Google Fotos.

- **Otimização de Vídeos**:
  - Comprime vídeos usando o codec H.264 (libx264).
  - Reduz o tamanho de arquivos MP4, MOV, AVI e MKV.
  - Permite redimensionar vídeos para uma resolução máxima configurável.
  - Preserva metadados e arquivos JSON de metadados do Google Fotos.

- **Processamento Paralelo**:
  - Utiliza múltiplos núcleos da CPU para processar arquivos em paralelo, acelerando a otimização.

- **Backup dos Arquivos Originais**:
  - Opção para manter uma cópia dos arquivos originais em uma pasta de backup.

---

## Pré-requisitos

- **Python 3.6 ou superior**.
- Dependências do Python:
  - `Pillow` (para processamento de imagens).
  - `ffmpeg-python` (para processamento de vídeos).
  - `tqdm` (para exibir barras de progresso).

---

## Como Baixar os Dados do Google Fotos

1. Acesse o [Google Takeout](https://takeout.google.com/).
2. Selecione apenas o serviço **Google Fotos**.
3. Escolha o formato de download (recomendado `.zip`).
4. Aguarde o processamento e faça o download do arquivo.
5. Extraia o conteúdo do arquivo `.zip` em uma pasta no seu computador.

---

## Instalação das Dependências

1. Clone este repositório ou baixe o arquivo `otimizador-google-fotos.py`.
2. Instale as dependências necessárias usando o `pip`:

   ```bash
   pip install pillow ffmpeg-python tqdm
   ```

3. Certifique-se de que o `ffmpeg` está instalado no seu sistema. Para instalar no Windows, baixe o executável [aqui](https://ffmpeg.org/download.html) e adicione-o ao `PATH`.

---

## Como Usar

1. Execute o script passando a pasta de entrada (onde estão as mídias do Google Fotos) e a pasta de saída (onde os arquivos otimizados serão salvos):

   ```bash
   python otimizador-google-fotos.py "caminho/para/pasta_entrada" -o "caminho/para/pasta_saida"
   ```

2. **Argumentos Opcionais**:
   - `-o` ou `--pasta-saida`: Define a pasta de saída para os arquivos otimizados.
   - `-b` ou `--pasta-backup`: Define a pasta de backup para os arquivos originais.
   - `-j` ou `--qualidade-jpg`: Define a qualidade das imagens JPEG (padrão: 85).
   - `--converter-png`: Converte imagens PNG para JPEG.
   - `--sem-backup`: Não faz backup dos arquivos originais.
   - `-p` ou `--processos`: Define o número de processos paralelos (padrão: número de CPUs).
   - `--crf`: Define o fator de qualidade de vídeo (padrão: 23).
   - `--preset`: Define o preset de codificação de vídeo (padrão: `medium`).

   Exemplo completo:

   ```bash
   python otimizador-google-fotos.py "caminho/para/pasta_entrada" -o "caminho/para/pasta_saida" --sem-backup -j 90 --converter-png -p 4 --crf 20 --preset fast
   ```

3. Após a execução, os arquivos otimizados serão salvos na pasta de saída, e um relatório detalhado será gerado.

---

## Exemplo de Saída

Após a execução, você verá estatísticas como:

```
==================================================
ESTATÍSTICAS DE OTIMIZAÇÃO
==================================================
Tempo de processamento: 120.45 segundos
Arquivos processados: 500
  - Imagens otimizadas: 400 de 400
  - Vídeos otimizados: 100 de 100
  - Arquivos ignorados: 0
  - Erros: 0
Tamanho original: 1024.00 MB
Tamanho final: 512.00 MB
Espaço economizado: 512.00 MB (50.0%)
==================================================
Processo concluído! Arquivos otimizados salvos em: caminho/para/pasta_saida
Arquivos originais preservados em: caminho/para/pasta_backup
```

---

## Contribuições

Sugestões e contribuições são bem-vindas! Se você tiver ideias para melhorar este projeto, sinta-se à vontade para:

1. Abrir uma **issue** no GitHub.
2. Enviar um **pull request** com suas melhorias.

---

## Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.

---
