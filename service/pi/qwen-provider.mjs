// Public explicit-stream SDK path: preserve smaller caller limits while bypassing
// streamSimple's fixed4096-token reserve for this1024-token physical context.
export function streamQwen(runtime,model,context,options={}){
 const requested=options.maxTokens===undefined?128:options.maxTokens;
 if(!Number.isSafeInteger(requested)||requested<1)throw Error('invalid_output_budget');
 return runtime.stream(model,context,{...options,maxTokens:Math.min(requested,128),maxRetries:0,timeoutMs:45000});
}
