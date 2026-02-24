// pages/profile/profile.js
const { auth } = require('../../utils/auth.js');

Page({
  data: {
    userInfo: {}
  },

  onLoad: function(options) {
    this.loadUserInfo();
  },

  onShow: function() {
    this.loadUserInfo();
  },

  // 加载用户信息
  loadUserInfo: function() {
    try {
      const userInfo = wx.getStorageSync('userInfo') || {};
      this.setData({
        userInfo: userInfo
      });
    } catch (error) {
      console.error('获取用户信息失败:', error);
    }
  },

  // 退出登录
  logout: async function() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await auth.logout();
            wx.showToast({
              title: '已退出',
              icon: 'success'
            });
            
            // 跳转到登录页
            setTimeout(() => {
              wx.redirectTo({
                url: '/pages/login/login'
              });
            }, 1500);
          } catch (error) {
            console.error('退出登录失败:', error);
            wx.showToast({
              title: '退出失败',
              icon: 'none'
            });
          }
        }
      }
    });
  },

  // 管理文件
  manageFiles: function() {
    wx.showModal({
      title: '文件管理',
      content: '您可以在对应的知识库中上传和管理文件',
      showCancel: false
    });
  },

  // 分享知识库
  shareKnowledgeBase: function() {
    wx.showModal({
      title: '分享知识库',
      content: '请输入要分享的知识库名称或选择知识库',
      editable: true,
      placeholderText: '输入知识库名称',
      success: (res) => {
        if (res.confirm && res.content) {
          // 这里可以实现知识库分享逻辑
          wx.setClipboardData({
            data: `邀请您加入知识库：${res.content}，链接：https://lingxi-kb.com/join/${Date.now()}`,
            success: () => {
              wx.showToast({
                title: '邀请链接已复制',
                icon: 'success'
              });
            }
          });
        }
      }
    });
  },

  // 管理账户
  manageAccount: function() {
    wx.showModal({
      title: '账号设置',
      content: '账号设置功能正在开发中...',
      showCancel: false
    });
  }
});