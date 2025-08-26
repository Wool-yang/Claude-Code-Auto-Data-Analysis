# 配置文件目录

本目录包含项目的各种配置文件和API密钥设置。

## 配置文件结构

- `config.example.json` - 配置模板文件，包含所有支持的配置项
- `config.json` - 实际配置文件（需要用户创建，包含真实的API密钥）

## 快速开始

1. 复制配置模板：
   ```bash
   cp config.example.json config.json
   ```

2. 编辑 `config.json`，填入你的API密钥和配置

## 支持的API服务

### 1. Gemini API（图片分析）

**用途**：用于分析和描述非结构化数据中的图片内容

**获取API密钥**：
1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 登录Google账号
3. 创建新的API密钥
4. 复制密钥到配置文件的 `gemini_api_key` 字段

**支持的图片格式**：
- PNG (image/png)
- JPEG (image/jpeg)
- WEBP (image/webp) 
- HEIC (image/heic)
- HEIF (image/heif)

### 2. 其他API服务（预留扩展）

本配置系统支持扩展更多API服务，例如：

- **OpenAI API**：用于文本分析和自然语言处理
- **Azure Cognitive Services**：用于文档OCR和内容理解
- **AWS Services**：用于云服务集成
- **其他自定义API**：根据项目需求添加

## 配置文件示例

```json
{
  "gemini_api_key": "your-gemini-api-key-here",
  "openai_api_key": "your-openai-api-key-here",
  "azure_cognitive_services": {
    "endpoint": "https://your-resource.cognitiveservices.azure.com/",
    "api_key": "your-azure-api-key-here"
  },
  "aws_services": {
    "access_key_id": "your-aws-access-key-id",
    "secret_access_key": "your-aws-secret-access-key",
    "region": "us-east-1"
  },
  "custom_apis": {
    "service_name": {
      "endpoint": "https://api.example.com/v1/",
      "api_key": "your-custom-api-key",
      "additional_config": "value"
    }
  }
}
```

## 安全注意事项

- **配置文件安全**：`config.json` 已添加到 `.gitignore`，不会被提交到版本控制
- **API密钥保护**：请勿在代码中硬编码API密钥，始终使用配置文件
- **访问权限**：确保配置文件的访问权限仅限于必要的用户和进程
- **密钥轮换**：定期更换API密钥以提高安全性

## 添加新的API配置

如需添加新的API服务配置：

1. **更新配置模板**：在 `config.example.json` 中添加新的配置项
2. **更新文档**：在本README中添加相应的配置说明
3. **实现代码**：在相关的工具脚本中添加API调用逻辑
4. **测试验证**：确保新配置项正常工作并有合适的错误处理