// app.js
App({
  globalData: {
    userInfo: null,
    token: null,
    currentKnowledgeBase: null
  },

  onLaunch: function () {
    // App启动时的逻辑
    this.checkLoginStatus();
  },

  onShow: function (options) {
    // 当小程序启动，或从后台进入前台显示
  },

  onHide: function () {
    // 当小程序从前台进入后台
  },

  // 检查登录状态
  checkLoginStatus: function() {
    const token = wx.getStorageSync('token');
    if (token) {
      this.globalData.token = token;
      // 获取用户信息
      const userInfo = wx.getStorageSync('userInfo');
      if (userInfo) {
        this.globalData.userInfo = userInfo;
      }
    }
  },

  // 设置用户信息
  setUserInfo: function(userInfo) {
    this.globalData.userInfo = userInfo;
    wx.setStorageSync('userInfo', userInfo);
  },

  // 设置token
  setToken: function(token) {
    this.globalData.token = token;
    wx.setStorageSync('token', token);
  },

  // 清除登录信息
  clearLoginInfo: function() {
    this.globalData.userInfo = null;
    this.globalData.token = null;
    wx.removeStorageSync('userInfo');
    wx.removeStorageSync('token');
  }
})