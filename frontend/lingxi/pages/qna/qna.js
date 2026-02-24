// pages/qna/qna.js
const { api } = require('../../utils/api.js');

Page({
  data: {
    knowledgeBaseId: '',
    knowledgeBaseName: '',
    messages: [],
    inputValue: '',
    inputValid: false,  // 添加输入有效性标志
    sending: false,
    scrollTop: 0
  },

  onLoad: function(options) {
    // 获取知识库ID和名称
    const knowledgeBaseId = options.knowledgeBaseId;
    const knowledgeBaseName = decodeURIComponent(options.knowledgeBaseName || '');
    
    this.setData({
      knowledgeBaseId,
      knowledgeBaseName
    });
    
    // 添加欢迎消息
    this.setData({
      messages: [{
        id: 'welcome',
        role: 'assistant',
        content: `您好！这是${knowledgeBaseName}知识库问答页面，您可以基于知识库内容提问。`
      }]
    });
  },

  onInput: function(e) {
    const value = e.detail.value;
    this.setData({
      inputValue: value,
      inputValid: value.trim() !== ''  // 更新输入有效性标志
    });
  },

  // 发送问题
  sendQuestion: async function() {
    const question = this.data.inputValue.trim();
    const knowledgeBaseId = this.data.knowledgeBaseId;
    
    // 检查输入和状态
    if (!question) {
      wx.showToast({
        title: '请输入问题',
        icon: 'none'
      });
      return;
    }
    
    if (this.data.sending) {
      return; // 如果正在发送，则不处理新请求
    }
    
    // 检查是否选择了知识库
    if (!knowledgeBaseId) {
      wx.showToast({
        title: '请先选择知识库',
        icon: 'none'
      });
      return;
    }
    
    this.setData({ sending: true });
    
    // 添加用户消息到聊天记录
    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: question
    };
    
    const newMessages = [...this.data.messages, userMessage];
    this.setData({ 
      messages: newMessages,
      inputValue: '',
      inputValid: false  // 清空输入后，输入无效
    });
    
    try {
      // 发送问题到后端
      const result = await api.askQuestion(question, knowledgeBaseId);
      
      // 添加助手回复到聊天记录
      const assistantMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: result.answer || '未能获取答案，请稍后重试。'
      };
      
      const updatedMessages = [...newMessages, assistantMessage];
      this.setData({ 
        messages: updatedMessages,
        sending: false 
      });
      
      // 滚动到底部
      this.setData({
        scrollTop: 999999
      });
    } catch (error) {
      console.error('提问失败:', error);
      
      // 添加错误消息到聊天记录
      const errorMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: '提问失败：' + (error.message || '网络错误')
      };
      
      const updatedMessages = [...newMessages, errorMessage];
      this.setData({ 
        messages: updatedMessages,
        sending: false 
      });
    }
  },

  // 滚动到底部
  scrollToLower: function() {
    // 滚动到底部
    this.setData({
      scrollTop: 999999
    });
  },

  // 清空输入
  clearInput: function() {
    this.setData({
      inputValue: '',
      inputValid: false
    });
  }
});