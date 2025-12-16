import axios from 'axios'

const service = axios.create({
  baseURL: 'http://localhost:8000', 
  timeout: 5000
})

export const api = {
  // 从games文件夹获取
  getData: () => {
    return service.get('/api/games')
  },
  
  // 发送数据接口保持不变
  sendData: (name, value) => {
    return service.post('/api/process', { name, value })
  }
}