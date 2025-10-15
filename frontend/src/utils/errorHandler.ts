/**
    *    统一的错误处理工具
    */
import    {    ElMessage    }    from    'element-plus'
import    type    {    AxiosError    }    from    'axios'

/**    API    错误响应接口    */
interface    ApiErrorResponse    {
                success:    false
                message:    string
                details?:    Record<string,    any>
}

/**    错误处理配置    */
interface    ErrorHandlerOptions    {
                showMessage?:    boolean    //    是否显示错误消息
                logError?:    boolean    //    是否记录错误
                customMessage?:    string    //    自定义错误消息
                duration?:    number    //    消息显示时长（毫秒）
}

/**
    *    统一的    API    错误处理函数
    *    @param    error    -    错误对象
    *    @param    operation    -    操作名称
    *    @param    options    -    错误处理选项
    */
export    function    handleApiError(
                error:    any,
                operation:    string,
                options:    ErrorHandlerOptions    =    {}
):    void    {
                const    {
                                showMessage    =    true,
                                logError    =    true,
                                customMessage,
                                duration    =    3000
                }    =    options

                let    errorMessage    =    customMessage    ||    `${operation}失败`

                //    解析错误消息
                if    (error    &&    typeof    error    ===    'object')    {
                                const    axiosError    =    error    as    AxiosError<ApiErrorResponse>

                                if    (axiosError.response)    {
                                                //    服务器返回错误响应
                                                const    status    =    axiosError.response.status
                                                const    data    =    axiosError.response.data

                                                if    (data    &&    typeof    data    ===    'object'    &&    'message'    in    data)    {
                                                                errorMessage    =    data.message    ||    errorMessage
                                                }    else    {
                                                                //    根据状态码提供默认消息
                                                                errorMessage    =    getDefaultErrorMessage(status,    operation)
                                                }
                                }    else    if    (axiosError.request)    {
                                                //    请求已发送但没有响应
                                                errorMessage    =    '服务器无响应，请检查网络连接'
                                }    else    {
                                                //    其他错误
                                                errorMessage    =    error.message    ||    errorMessage
                                }
                }

                //    记录错误
                if    (logError)    {
                                console.error(`[${operation}]    错误:`,    error)
                }

                //    显示错误消息
                if    (showMessage)    {
                                ElMessage.error({
                                                message:    errorMessage,
                                                duration
                                })
                }
}

/**
    *    根据HTTP状态码获取默认错误消息
    *    @param    status    -    HTTP状态码
    *    @param    operation    -    操作名称
    */
function    getDefaultErrorMessage(status:    number,    operation:    string):    string    {
                const    messages:    Record<number,    string>    =    {
                                400:    '请求参数错误',
                                401:    '未授权，请重新登录',
                                403:    '没有权限执行此操作',
                                404:    '请求的资源不存在',
                                408:    '请求超时',
                                500:    '服务器内部错误',
                                502:    '网关错误',
                                503:    '服务暂时不可用',
                                504:    '网关超时'
                }

                return    messages[status]    ||    `${operation}失败    (状态码:    ${status})`
}

/**
    *    创建异步操作包装器，自动处理错误
    *    @param    operation    -    操作名称
    *    @param    fn    -    异步函数
    *    @param    options    -    错误处理选项
    */
export    function    createAsyncHandler<T    extends    any[],    R>(
                operation:    string,
                fn:    (...args:    T)    =>    Promise<R>,
                options:    ErrorHandlerOptions    =    {}
):    (...args:    T)    =>    Promise<R    |    null>    {
                return    async    (...args:    T):    Promise<R    |    null>    =>    {
                                try    {
                                                return    await    fn(...args)
                                }    catch    (error)    {
                                                handleApiError(error,    operation,    options)
                                                return    null
                                }
                }
}

/**
    *    表单验证错误处理
    *    @param    error    -    验证错误对象
    */
export    function    handleValidationError(error:    Record<string,    string[]>):    void    {
                const    messages    =    Object.entries(error)
                                .map(([field,    errors])    =>    `${field}:    ${errors.join(',    ')}`)
                                .join('\n')

                ElMessage.error({
                                message:    messages,
                                duration:    4000,
                                dangerouslyUseHTMLString:    false
                })
}

/**
    *    网络错误检查
    *    @param    error    -    错误对象
    */
export    function    isNetworkError(error:    any):    boolean    {
                return    (
                                error    &&
                                typeof    error    ===    'object'    &&
                                'request'    in    error    &&
                                !error.response
                )
}

/**
    *    超时错误检查
    *    @param    error    -    错误对象
    */
export    function    isTimeoutError(error:    any):    boolean    {
                return    (
                                error    &&
                                typeof    error    ===    'object'    &&
                                (error.code    ===    'ECONNABORTED'    ||    error.message?.includes('timeout'))
                )
}

/**
    *    成功消息提示
    *    @param    message    -    消息内容
    *    @param    duration    -    显示时长
    */
export    function    showSuccessMessage(message:    string,    duration    =    2000):    void    {
                ElMessage.success({
                                message,
                                duration
                })
}

/**
    *    警告消息提示
    *    @param    message    -    消息内容
    *    @param    duration    -    显示时长
    */
export    function    showWarningMessage(message:    string,    duration    =    2500):    void    {
                ElMessage.warning({
                                message,
                                duration
                })
}
