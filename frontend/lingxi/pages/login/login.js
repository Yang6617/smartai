// pages/login/login.js
const { auth } = require('../../utils/auth.js');

Page({
  data: {
    isLoggingIn: false,
    loginError: ''
  },

  onLoad: function(options) {
    // 页面加载时的逻辑
  },

  // 微信登录（带用户信息）
  onWechatLoginWithUserInfo: async function(e) {
    if (this.data.isLoggingIn) return;
    
    // 检查用户是否授权了用户信息
    if (!e.detail.userInfo) {
      // 用户拒绝了授权，可以提示用户需要授权才能使用完整功能
      wx.showModal({
        title: '提示',
        content: '您需要授权用户信息才能使用完整功能',
        showCancel: false
      });
      this.setData({
        isLoggingIn: false
      });
      return;
    }
    
    this.setData({
      isLoggingIn: true,
      loginError: ''
    });
    
    try {
      // 获取微信登录code
      const loginRes = await auth.wxLogin();
      const code = loginRes.code;
      
      // 调用后端登录接口
      const result = await auth.wechatLoginWithCode(code);
      
      if (result.access_token) {
        // 保存token
        wx.setStorageSync('token', result.access_token);
        
        // 保存用户信息
        const userInfo = e.detail.userInfo;
        wx.setStorageSync('userInfo', userInfo);
        
        // 保存到全局
        const app = getApp();
        app.setUserInfo(userInfo);
        app.setToken(result.access_token);
        
        // 更新用户信息到服务器
        await auth.updateUserInfoToServer(userInfo);
        
        // 显示成功提示
        wx.showToast({
          title: '登录成功',
          icon: 'success',
          duration: 1500,
          success: () => {
            // 跳转到首页
            setTimeout(() => {
              wx.switchTab({
                url: '/pages/knowledge/knowledge'
              });
            }, 1500);
          }
        });
      } else {
        throw new Error(result.message || '登录失败');
      }
    } catch (error) {
      console.error('登录失败:', error);
      this.setData({
        loginError: error.message || '登录失败，请重试',
        isLoggingIn: false
      });
    }
  }
});