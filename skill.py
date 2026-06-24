# Python编程智能体配置文件
agent:
  name: "PythonCodingAssistant"
  version: "2.0"
  
  # 模型配置
  model:
    base: "deepseek-v3.2"
    mode: "reasoner"  # 使用思考模式，适合复杂编程任务
    temperature: 0.3   # 较低温度保证代码稳定性
  
  # 记忆系统
  memory:
    short_term:
      type: "vector_db"
      backend: "chroma"
      max_turns: 20
    long_term:
      type: "user_profile"
      storage: "redis"
      update_frequency: "daily"
    
  # 用户习惯学习
  habit_learning:
    enabled: true
    auto_complete: true
    learning_rate: 0.1
    features:
      - "preferred_libraries"
      - "coding_style"
      - "error_handling_patterns"
      - "test_frameworks"
    
  # 工具集成
  tools:
    - "code_executor"
    - "debugger"
    - "package_manager"
    - "documentation_generator"
  
  # 自动补全规则
  auto_completion:
    rules:
      - trigger: "web_scraping|爬虫"
        add: ["requests", "BeautifulSoup", "异常处理"]
      - trigger: "data_analysis|数据分析"
        add: ["pandas", "numpy", "matplotlib"]
      - trigger: "机器学习|ml"
        add: ["scikit-learn", "train_test_split", "评估指标"]