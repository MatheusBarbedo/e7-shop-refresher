# E7 Shop Refresher

Automatiza o *refresh* e a compra na **Secret Shop** do Epic Seven, comprando
automaticamente **Covenant Bookmarks** e **Mystic Medals** enquanto você gasta
uma quantidade definida de skystones. Interface gráfica com controle de
velocidade, pausar/retomar/encerrar e status ao vivo.

Baseado no [E7AutoBuy original](https://github.com/senkkou/E7AutoBuy), com
correções para funcionar em emuladores modernos como o **MuMu Player Nx**
(que usa múltiplos displays virtuais).

---

## Instalação (recomendado)

Baixe o instalador na aba [Releases](../../releases) deste repositório,
rode o `.exe` e siga o assistente. ADB e Tesseract OCR já vêm inclusos —
não precisa instalar nada além do próprio programa.

## Emuladores compatíveis

| Emulador | Status | Observação |
|---|---|---|
| **MuMu Player Nx** | ✅ | Suportado via detecção automática de display (multi-display) |
| **MuMu Player 12** | ✅ | Display único, funciona direto |
| **LDPlayer** | ✅ | Recomendado; suportado desde o projeto original |
| **BlueStacks** | ⚠️ | Funciona, mas algumas versões têm o ADB com problema |
| **Nox** | ✅ | Deve funcionar (ADB padrão) |

**Requisitos do emulador:**
- **ADB habilitado** (depuração via ADB ligada nas configurações do emulador).
- **Resolução 16:9** — 1280x720, 1920x1080 ou 2560x1080.
- **Epic Seven em inglês** (o reconhecimento de texto procura "Covenant
  Bookmarks" e "Mystic Medals").

---

## Passo a passo

1. **Abra o emulador** e habilite o **ADB** (ex.: no MuMu → Configurações →
   Outras configurações → Depuração ADB; no LDPlayer → Configurações → Outras
   configurações → ADB).
2. **Coloque o Epic Seven em inglês** (configurações do jogo) e entre na conta.
3. **Vá até a Secret Shop** (Loja Secreta) e deixe essa tela aberta.
4. **Abra o programa** (atalho instalado ou `AutoBuy.bat`).
5. **Preencha:**
   - **Skystones a gastar** — quanto quer gastar (cada refresh custa 3; ele
     calcula os refreshes sozinho).
   - **Delay** — velocidade. Menor = mais rápido (padrão 1.5). Se começar a
     errar cliques, aumente um pouco.
6. Clique **Iniciar**. Durante a execução você pode **Pausar/Retomar** e
   **Encerrar** a qualquer momento. O painel mostra refreshes, skystones,
   bookmarks e medals em tempo real.

O programa detecta sozinho o device e o display do E7 a cada execução, e se
conecta ao ADB automaticamente.

---

## Arquivos do projeto

- `autobuy_gui.py` — interface gráfica (Iniciar/Pausar/Encerrar + status e log).
- `e7core.py` — núcleo da automação (ADB, detecção de display, OCR, compras).
- `AutoBuy.bat` — atalho que abre a interface (sem console).
- `assets/gen_icon.py` — gera o ícone do app.
- `E7ShopRefresher.spec`, `build.bat`, `installer.iss` — empacotamento
  (PyInstaller + Inno Setup).

## Rodando pelo código (desenvolvimento)

Requer Python 3:

```bash
pip install -r requirements.txt
python autobuy_gui.py
```

Baixe também o [Android Platform Tools (ADB)](https://developer.android.com/tools/releases/platform-tools)
e o [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) e extraia-os
nas pastas `platform-tools/` e `tesseract/` na raiz do projeto (mesmos nomes
usados em `e7core.py` e `installer.iss`).

### Gerando o instalador

```bash
build.bat
```

Gera o executável com PyInstaller e o instalador com Inno Setup em
`installer_output/`. Requer o [Inno Setup 6](https://jrsoftware.org/isinfo.php)
instalado e as pastas `platform-tools/` e `tesseract/` presentes.

---

## Correções em relação ao original

O MuMu Nx expõe vários displays virtuais (launcher + apps), o que quebrava o
bot. Foram corrigidos:

1. **Screenshot corrompido** — o `screencap` vinha com um aviso de "multiple
   displays" antes do PNG; agora o código corta tudo antes do cabeçalho PNG.
2. **Cliques iam para a home** — os toques iam ao display padrão (launcher);
   agora usam `input -d <id_lógico>` no display do E7.
3. **Swipe não funcionava** — sintaxe corrigida para `input -d <id> swipe`.
4. **Conexão automática ao ADB** e seleção de um único device (evita o erro
   "more than one device/emulator").

Além disso: interface gráfica, entrada por skystones, controle de velocidade
(delay), pausar/retomar/encerrar e execução sem janela de console.

---

## Créditos

- Projeto original: **[E7AutoBuy](https://github.com/senkkou/E7AutoBuy)** por
  [senkkou](https://github.com/senkkou) — toda a lógica base de reroll/compra
  e o mapeamento da Secret Shop vieram dele.
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — reconhecimento
  de texto.
- [Android Platform Tools (ADB)](https://developer.android.com/tools/releases/platform-tools)
  — comunicação com o emulador.

Adaptação para MuMu Nx, interface gráfica e melhorias por **Matheus Barbedo**.
