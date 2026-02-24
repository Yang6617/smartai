// pages/knowledge/knowledge.js
const { api } = require('../../utils/api.js');

Page({
  data: {
    knowledgeBases: []
  },

  onLoad: function(options) {
    this.loadKnowledgeBases();
  },

  onShow: function() {
    // 页面显示时刷新知识库列表
    this.loadKnowledgeBases();
  },

  // 加载知识库列表
  loadKnowledgeBases: async function() {
    try {
      const result = await api.getKnowledgeBases();
      this.setData({
        knowledgeBases: result || []  // The API returns the list directly
      });
    } catch (error) {
      console.error('加载知识库列表失败:', error);
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    }
  },

  // 创建新知识库（群组）
  createKnowledgeBase: function() {
    wx.showModal({
      title: '创建知识库',
      editable: true,
      placeholderText: '请输入知识库名称',
      success: async (res) => {
        if (res.confirm && res.content) {
          try {
            await api.createKnowledgeBase({
              name: res.content,
              description: res.content + ' 知识库'
            });
            wx.showToast({
              title: '创建成功',
              icon: 'success'
            });
            // 刷新列表
            this.loadKnowledgeBases();
          } catch (error) {
            console.error('创建知识库失败:', error);
            wx.showToast({
              title: '创建失败',
              icon: 'none'
            });
          }
        }
      }
    });
  },

  // 进入知识库详情
  enterKnowledgeBase: function(event) {
    const id = event.currentTarget.dataset.id;
    const kb = this.data.knowledgeBases.find(kb => kb.id === id);
    
    // 设置全局当前知识库
    const app = getApp();
    app.globalData.currentKnowledgeBase = kb;
    
    // 跳转到问答页面
    wx.navigateTo({
      url: `/pages/index/index?knowledgeBaseId=${id}&knowledgeBaseName=${encodeURIComponent(kb.name || kb.title)}`
    });
  }
});