# x-Ollama-Voice-Mac  
一款完全离线运行的语音助手，集成了 Whisper、Ollama 和 pyttsx3 模型，支持离线语音识别、自然语言处理及文本转语音（TTS）功能。
结合 **Mistral 7b**（通过 Ollama 实现）和 **Whisper** 语音识别模型构建而成。此项目基于 [maudoin 的优秀工作](https://github.com/apeatling/ollama-voice-mac)，添加了对 Mac 的兼容性并进行了一系列改进。

https://github.com/apeatling/ollama-voice-mac/assets/1464705/996abeb7-7e99-451b-8d3b-feb3fecbb82e  

---

## 安装与运行  
### 0. 在mac上安装python的虚拟环境 python版本：3.11
```bash
python3.11 -m venv myenv_311
source myenv_311/bin/activate
deactivate
```

### 1. 安装 Ollama  
在 Mac 上安装 [Ollama](https://ollama.ai)。  

### 2. 下载 Mistral 7b 模型  
运行以下命令下载模型：  
```bash
ollama pull mistral
```  

### 3. 下载 Whisper 模型  
访问 [Whisper 模型库](https://github.com/openai/whisper/discussions/63#discussioncomment-3798552)，选择适合的模型（`base` 即可）。  

### 4. 克隆本项目  
将项目代码克隆到本地计算机：  
```bash
git clone <仓库地址>
```  

### 5. 配置 Whisper 模型路径  
将 Whisper 模型放入项目根目录的 `/whisper` 文件夹中。  

### 6. 安装 Python 和 Pip  
确保已安装 [Python](https://www.python.org/downloads/macos/) 和 [Pip](https://pip.pypa.io/en/stable/installation/)。  

### 7. 配置 PyAudio 库（Apple Silicon 特别步骤）  
对于 Apple Silicon 用户，需安装 **Homebrew** 并运行以下命令：  
```bash
brew install portaudio
```  

### 8. 安装依赖  
运行以下命令安装所需依赖：  
```bash
pip install -r requirements.txt
```  

### 9. 启动助手  
运行以下命令启动语音助手：  
```bash
python assistant.py
```  


### 10. 中间使用的要点：
```yaml
语音识别：使用 Whisper 模型进行本地语音识别，完全离线运行。
自然语言处理：使用 Ollama 平台运行 Mistral 7b 模型，实现高效的本地大语言模型推理，无需联网。
文本转语音（TTS）：基于 pyttsx3 实现的离线文本语音合成功能，支持多种语言和语音优化。但是 pyttsx3 太机械了 增加了edge-tts
```  

---

## 提升语音质量  

在 MacOS 14 Sonoma 中，可以通过以下步骤提升语音质量：  

1. 打开 **系统设置** > **辅助功能** > **语音内容**。  
2. 选择 **系统语音** 并点击 **管理语音**。  
3. 在英文语音中找到 **"Zoe (Premium)"** 并下载。  
4. 下载完成后，将系统语音更改为 **Zoe (Premium)**。  

---

## 支持其他语言  

要支持其他语言，可以通过以下方式配置：  

1. 编辑 `assistant.yaml` 文件。  
2. 下载目标语言的 Whisper 模型并将其路径更新到 `modelPath` 配置项。  

**示例（中文配置）**：  
- 下载适合中文的 Whisper 模型，例如 `medium.zh`。  
- 在 `assistant.yaml` 中将 `modelPath` 修改为下载的模型路径，例如：  
  ```yaml
  modelPath: /path/to/medium.zh.pt
  ```  