// utils/auth.js
const { api } = require('./api.js');

// 认证相关的工具函数
const auth = {
  // 检查是否已登录
  isAuthenticated: function() {
    const token = wx.getStorageSync('token');
    return !!token;
  },
  
  // 获取用户信息
  getUserInfo: function() {
    return new Promise((resolve, reject) => {
      const userInfo = wx.getStorageSync('userInfo');
      if (userInfo) {
        resolve(userInfo);
      } else {
        reject(new Error('用户信息未授权'));
      }
    });
  },
  
  // 获取用户信息（用于登录流程）- 兼容旧方法名
  getUserProfile: function() {
    return this.getUserInfo();
  },
  
  // 微信登录（获取code）
  wxLogin: function() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (res) => {
          if (res.code) {
            resolve(res);  // 返回完整的res对象 which contains the code
          } else {
            reject(new Error('获取登录code失败'));
          }
        },
        fail: (error) => {
          reject(new Error('微信登录失败: ' + error.errMsg));
        }
      });
    });
  },
  
  // 微信登录并获取用户信息
  wechatLoginWithCode: function(code) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: 'http://127.0.0.1:8002/wechat/login',
        method: 'POST',
        data: {
          code: code
        },
        header: {
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data);
          } else {
            reject(new Error(`登录失败: ${res.data?.detail || '未知错误'}`));
          }
        },
        fail: (error) => {
          reject(error);
        }
      });
    });
  },
  
  // 更新用户信息到服务器
  updateUserInfoToServer: function(userInfo) {
    return new Promise((resolve, reject) => {
      // 这里可以根据需要更新用户信息到服务器
      resolve();
    });
  },
  
  // 退出登录
  logout: function() {
    return new Promise((resolve) => {
      // 清除本地存储
      wx.clearStorage();
      
      // 重置全局数据
      getApp().globalData.userInfo = null;
      getApp().globalData.token = null;
      
      resolve();
    });
  }
};

module.exports = {
  auth: auth
};