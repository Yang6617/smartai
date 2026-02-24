// pages/index/index.js
const { api } = require('../../utils/api.js');

Page({
  data: {
    knowledgeBaseId: '',
    knowledgeBaseName: '',
    fileList: [],
    selectedFile: null,
    uploading: false,
    showUploadModalFlag: false
  },


  onLoad: function(options) {
    // 获取知识库ID和名称
    const knowledgeBaseId = options.knowledgeBaseId;
    const knowledgeBaseName = decodeURIComponent(options.knowledgeBaseName || '');
    
    this.setData({
      knowledgeBaseId,
      knowledgeBaseName
    });
    
    // 加载文件列表
    this.loadFileList();
  },

  onShow: function() {
    // 页面显示时刷新文件列表
    this.loadFileList();
  },

  // 加载文件列表
  loadFileList: async function() {
    try {
      const result = await api.getFileList(this.data.knowledgeBaseId);
      this.setData({
        fileList: result || []
      });
    } catch (error) {
      console.error('加载文件列表失败:', error);
      this.setData({
        fileList: []
      });
    }
  },

  // 跳转到问答页面
  goToQnaPage: function() {
    const { knowledgeBaseId, knowledgeBaseName } = this.data;
    wx.navigateTo({
      url: `/pages/qna/qna?knowledgeBaseId=${knowledgeBaseId}&knowledgeBaseName=${encodeURIComponent(knowledgeBaseName)}`
    });
  },

  // 显示上传模态框
  showUploadModal: function() {
    this.setData({
      showUploadModalFlag: true,
      selectedFile: null
    });
  },

  // 隐藏上传模态框
  hideUploadModal: function() {
    this.setData({
      showUploadModalFlag: false,
      selectedFile: null
    });
  },

  // 阻止事件冒泡
  stopPropagation: function() {
    // 在微信小程序中，直接返回即可阻止事件冒泡
    return;
  },

  // 选择文件
  chooseFile: async function() {
    // 在调用API前确保模态框状态
    this.setData({
      showUploadModalFlag: true
    });

    try {
      // 使用chooseMessageFile API来选择聊天中接收的文件
      const result = await wx.chooseMessageFile({
        count: 1,
        type: 'file',
        extension: ['pdf', 'doc', 'docx', 'txt', 'md', 'xlsx', 'xls', 'ppt', 'pptx']
      });

      if (result && result.tempFiles && result.tempFiles.length > 0) {
        const file = result.tempFiles[0];
        this.setData({
          selectedFile: {
            path: file.path,
            name: file.name,
            size: file.size
          }
        });
      }
    } catch (error) {
      console.error('选择文件失败:', error);
      // 即使失败也要确保模态框保持显示
      this.setData({
        showUploadModalFlag: true
      });
      // 根据错误类型给出不同提示
      if (error.errMsg && error.errMsg.includes('cancel')) {
        // 用户取消选择
        console.log('用户取消选择文件');
      } else {
        wx.showToast({
          title: error.errMsg ? '文件选择失败' : '请在手机上使用此功能',
          icon: 'none',
          duration: 2000
        });
      }
    }
  },

  // 上传文件
  uploadFile: async function() {
    if (!this.data.selectedFile) {
      wx.showToast({
        title: '请选择文件',
        icon: 'none'
      });
      return;
    }

    const { selectedFile, knowledgeBaseId } = this.data;

    this.setData({ uploading: true });

    try {
      // 上传文件
      const result = await api.uploadFile(
        selectedFile.path,
        knowledgeBaseId,
        selectedFile.name  // 传递原始文件名
      );

      wx.showToast({
        title: '上传成功',
        icon: 'success'
      });

      // 刷新文件列表
      this.loadFileList();

      // 关闭模态框
      this.setData({
        showUploadModalFlag: false,
        selectedFile: null,
        uploading: false
      });
    } catch (error) {
      console.error('上传文件失败:', error);
      wx.showToast({
        title: '上传文件失败: ' + (error.message || '未知错误'),
        icon: 'none'
      });
      this.setData({ uploading: false });
    }
  }
});