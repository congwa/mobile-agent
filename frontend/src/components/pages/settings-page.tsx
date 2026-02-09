import { useEffect, useState } from "react";
import {
  Save,
  TestTube,
  RefreshCw,
  Brain,
  Server,
  Cpu,
  Layers,
  Loader2,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { cn } from "@/utils/tailwind";
import { useSettingsStore } from "@/stores/settings-store";

export default function SettingsPage() {
  const {
    settings,
    loading,
    saving,
    testResult,
    testLoading,
    reconnectLoading,
    reconnectResult,
    fetchSettings,
    updateSettings,
    testLLM,
    reconnectMCP,
    clearTestResult,
    clearReconnectResult,
  } = useSettingsStore();

  // 本地表单状态
  const [llmModel, setLlmModel] = useState("");
  const [llmApiKey, setLlmApiKey] = useState("");
  const [llmBaseUrl, setLlmBaseUrl] = useState("");
  const [mcpUrl, setMcpUrl] = useState("");
  const [agentMaxIter, setAgentMaxIter] = useState(20);
  const [agentPrompt, setAgentPrompt] = useState("");
  const [mwOperationLogger, setMwOperationLogger] = useState(true);
  const [mwScreenshotOpt, setMwScreenshotOpt] = useState(true);
  const [mwScreenshotMax, setMwScreenshotMax] = useState(2);
  const [mwRetry, setMwRetry] = useState(true);
  const [mwRetryMax, setMwRetryMax] = useState(2);
  const [mwRetryInterval, setMwRetryInterval] = useState(1.0);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  // 同步远程配置到本地表单
  useEffect(() => {
    if (!settings) return;
    setLlmModel(settings.llm.model);
    setLlmApiKey(settings.llm.api_key);
    setLlmBaseUrl(settings.llm.base_url);
    setMcpUrl(settings.mcp.url);
    setAgentMaxIter(settings.agent.max_iterations);
    setAgentPrompt(settings.agent.system_prompt);
    setMwOperationLogger(settings.middleware.operation_logger);
    setMwScreenshotOpt(settings.middleware.screenshot_optimizer);
    setMwScreenshotMax(settings.middleware.screenshot_max_consecutive);
    setMwRetry(settings.middleware.retry);
    setMwRetryMax(settings.middleware.retry_max_attempts);
    setMwRetryInterval(settings.middleware.retry_interval);
  }, [settings]);

  const handleSaveLLM = () => {
    updateSettings({
      llm: { model: llmModel, api_key: llmApiKey, base_url: llmBaseUrl },
    });
  };

  const handleSaveMCP = () => {
    updateSettings({
      mcp: { url: mcpUrl },
    });
  };

  const handleSaveAgent = () => {
    updateSettings({
      agent: { max_iterations: agentMaxIter, system_prompt: agentPrompt },
    });
  };

  const handleSaveMiddleware = () => {
    updateSettings({
      middleware: {
        operation_logger: mwOperationLogger,
        screenshot_optimizer: mwScreenshotOpt,
        screenshot_max_consecutive: mwScreenshotMax,
        retry: mwRetry,
        retry_max_attempts: mwRetryMax,
        retry_interval: mwRetryInterval,
      },
    });
  };

  if (loading && !settings) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-auto">
      <div className="border-b border-border bg-card/50 px-6 py-4">
        <h1 className="text-lg font-semibold text-foreground">设置</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          配置 LLM、MCP Server、Agent 行为和中间件
        </p>
      </div>

      <div className="flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-2xl space-y-6">
          {/* LLM 配置 */}
          <section className="rounded-lg border border-border bg-card p-5">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10">
                <Brain className="h-4 w-4 text-blue-500" />
              </div>
              <h2 className="text-sm font-semibold text-foreground">LLM 配置</h2>
            </div>
            <div className="space-y-4">
              <FormField label="模型">
                <input
                  type="text"
                  value={llmModel}
                  onChange={(e) => setLlmModel(e.target.value)}
                  placeholder="openai:gpt-4o"
                  className="w-full rounded-md border border-border bg-secondary/50 px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </FormField>
              <FormField label="API Key">
                <input
                  type="password"
                  value={llmApiKey}
                  onChange={(e) => setLlmApiKey(e.target.value)}
                  className="w-full rounded-md border border-border bg-secondary/50 px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </FormField>
              <FormField label="Base URL">
                <input
                  type="text"
                  value={llmBaseUrl}
                  onChange={(e) => setLlmBaseUrl(e.target.value)}
                  placeholder="https://api.openai.com/v1"
                  className="w-full rounded-md border border-border bg-secondary/50 px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </FormField>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { clearTestResult(); testLLM(); }}
                  disabled={testLoading}
                  className="flex items-center gap-1.5 rounded-md bg-blue-500/10 px-3 py-1.5 text-xs text-blue-400 hover:bg-blue-500/20 transition-colors cursor-pointer disabled:opacity-40"
                >
                  {testLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <TestTube className="h-3.5 w-3.5" />}
                  测试连接
                </button>
                <button
                  onClick={handleSaveLLM}
                  disabled={saving}
                  className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90 transition-colors cursor-pointer disabled:opacity-40"
                >
                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                  保存
                </button>
                {testResult && (
                  <span className={cn("flex items-center gap-1 text-xs", testResult.success ? "text-green-500" : "text-red-500")}>
                    {testResult.success ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                    {testResult.message}
                    {testResult.latency_ms > 0 && ` (${testResult.latency_ms}ms)`}
                  </span>
                )}
              </div>
            </div>
          </section>

          {/* MCP Server 配置 */}
          <section className="rounded-lg border border-border bg-card p-5">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10">
                <Server className="h-4 w-4 text-purple-500" />
              </div>
              <h2 className="text-sm font-semibold text-foreground">MCP Server 配置</h2>
            </div>
            <div className="space-y-4">
              <FormField label="MCP Server URL (SSE)">
                <input
                  type="text"
                  value={mcpUrl}
                  onChange={(e) => setMcpUrl(e.target.value)}
                  placeholder="http://localhost:3100/sse"
                  className="w-full rounded-md border border-border bg-secondary/50 px-3 py-2 font-mono text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </FormField>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSaveMCP}
                  disabled={saving}
                  className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90 transition-colors cursor-pointer disabled:opacity-40"
                >
                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                  保存
                </button>
                <button
                  onClick={() => { clearReconnectResult(); reconnectMCP(); }}
                  disabled={reconnectLoading}
                  className="flex items-center gap-1.5 rounded-md bg-purple-500/10 px-3 py-1.5 text-xs text-purple-400 hover:bg-purple-500/20 transition-colors cursor-pointer disabled:opacity-40"
                >
                  {reconnectLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                  重新连接
                </button>
                {reconnectResult && (
                  <span className={cn("flex items-center gap-1 text-xs", reconnectResult.success ? "text-green-500" : "text-red-500")}>
                    {reconnectResult.success ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                    {reconnectResult.message}
                  </span>
                )}
              </div>
            </div>
          </section>

          {/* Agent 配置 */}
          <section className="rounded-lg border border-border bg-card p-5">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10">
                <Cpu className="h-4 w-4 text-amber-500" />
              </div>
              <h2 className="text-sm font-semibold text-foreground">Agent 配置</h2>
            </div>
            <div className="space-y-4">
              <FormField label="最大迭代次数">
                <input
                  type="number"
                  value={agentMaxIter}
                  onChange={(e) => setAgentMaxIter(parseInt(e.target.value) || 0)}
                  className="w-32 rounded-md border border-border bg-secondary/50 px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </FormField>
              <FormField label="System Prompt">
                <textarea
                  value={agentPrompt}
                  onChange={(e) => setAgentPrompt(e.target.value)}
                  rows={6}
                  className="w-full resize-y rounded-md border border-border bg-secondary/50 px-3 py-2 font-mono text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </FormField>
              <button
                onClick={handleSaveAgent}
                disabled={saving}
                className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90 transition-colors cursor-pointer disabled:opacity-40"
              >
                {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                保存
              </button>
            </div>
          </section>

          {/* 中间件配置 */}
          <section className="rounded-lg border border-border bg-card p-5">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-green-500/10">
                <Layers className="h-4 w-4 text-green-500" />
              </div>
              <h2 className="text-sm font-semibold text-foreground">中间件配置</h2>
            </div>
            <div className="space-y-4">
              <ToggleRow
                label="操作日志 (OperationLogger)"
                description="记录每步操作的详细日志"
                checked={mwOperationLogger}
                onChange={setMwOperationLogger}
              />
              <div className="border-t border-border/50 pt-4">
                <ToggleRow
                  label="截图优化 (ScreenshotOptimizer)"
                  description="限制连续截图次数，避免无效重复截图"
                  checked={mwScreenshotOpt}
                  onChange={setMwScreenshotOpt}
                />
                {mwScreenshotOpt && (
                  <div className="mt-3 ml-6">
                    <FormField label="最大连续截图次数">
                      <input
                        type="number"
                        value={mwScreenshotMax}
                        onChange={(e) => setMwScreenshotMax(parseInt(e.target.value) || 0)}
                        className="w-24 rounded-md border border-border bg-secondary/50 px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </FormField>
                  </div>
                )}
              </div>
              <div className="border-t border-border/50 pt-4">
                <ToggleRow
                  label="工具重试 (Retry)"
                  description="工具调用失败时自动重试"
                  checked={mwRetry}
                  onChange={setMwRetry}
                />
                {mwRetry && (
                  <div className="mt-3 ml-6 flex gap-4">
                    <FormField label="最大重试次数">
                      <input
                        type="number"
                        value={mwRetryMax}
                        onChange={(e) => setMwRetryMax(parseInt(e.target.value) || 0)}
                        className="w-24 rounded-md border border-border bg-secondary/50 px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </FormField>
                    <FormField label="重试间隔 (秒)">
                      <input
                        type="number"
                        step="0.1"
                        value={mwRetryInterval}
                        onChange={(e) => setMwRetryInterval(parseFloat(e.target.value) || 0)}
                        className="w-24 rounded-md border border-border bg-secondary/50 px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </FormField>
                  </div>
                )}
              </div>
              <div className="border-t border-border/50 pt-4">
                <button
                  onClick={handleSaveMiddleware}
                  disabled={saving}
                  className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90 transition-colors cursor-pointer disabled:opacity-40"
                >
                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                  保存中间件配置
                </button>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function FormField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
        {label}
      </label>
      {children}
    </div>
  );
}

function ToggleRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={cn(
          "relative h-5 w-9 flex-shrink-0 rounded-full transition-colors cursor-pointer",
          checked ? "bg-primary" : "bg-border",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform",
            checked ? "left-[18px]" : "left-0.5",
          )}
        />
      </button>
    </div>
  );
}
