// utils/api.js
const BASE_URL = 'http://127.0.0.1:8002'; // 本地后端地址

// 统一请求封装
function request(options) {
  const token = wx.getStorageSync('token');
  
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json',
        ...options.header
      },
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else if (res.statusCode === 401) {
          // 未授权，跳转到登录页
          wx.redirectTo({
            url: '/pages/login/login'
          });
          reject(new Error('未授权，请重新登录'));
        } else {
          reject(new Error(`请求失败: ${res.statusCode}`));
        }
      },
      fail: (error) => {
        console.error('请求失败:', error);
        reject(error);
      }
    });
  });
}

// API 接口定义
const api = {
  // 用户相关
  login: (code) => request({
    url: '/wechat/login',
    method: 'POST',
    data: { code }
  }),
  
  // 群组相关（作为知识库使用）
  getKnowledgeBases: () => request({
    url: '/group/list',
    method: 'GET'
  }),
  
  createKnowledgeBase: (data) => request({
    url: '/group/create',
    method: 'POST',
    data: data
  }),
  
  // 文件相关
  uploadFile: (filePath, knowledgeBaseId, originalFileName) => {
    const token = wx.getStorageSync('token');
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: BASE_URL + '/file/upload',
        filePath: filePath,
        name: 'file',
        formData: {
          group_id: knowledgeBaseId,
          original_filename: originalFileName  // 传递原始文件名
        },
        header: {
          'Authorization': token ? `Bearer ${token}` : ''
        },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(JSON.parse(res.data));
          } else {
            reject(new Error('上传失败'));
          }
        },
        fail: (error) => {
          reject(error);
        }
      });
    });
  },
  
  getFileList: (knowledgeBaseId) => request({
    url: '/file/list',
    method: 'GET',
    data: { group_id: knowledgeBaseId }
  }),
  
  // 问答相关
  askQuestion: (question, knowledgeBaseId) => request({
    url: '/api/v1/ask-question',
    method: 'POST',
    data: { question, knowledge_base_id: knowledgeBaseId }
  }),
  
  getQaHistory: (limit = 20, offset = 0) => request({
    url: '/api/v1/qa/list',
    method: 'GET',
    data: { limit, offset }
  })
};

module.exports = {
  api: api,
  request: request
};