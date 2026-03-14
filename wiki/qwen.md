# Qwen Code

<h2>Table of contents</h2>

- [What is `Qwen Code`](#what-is-qwen-code)
- [Set up the `Qwen Code` (LOCAL)](#set-up-the-qwen-code-local)
  - [Set up the `Qwen Code` CLI (LOCAL)](#set-up-the-qwen-code-cli-local)
  - [Set up the `Qwen Code Companion` extension for `VS Code`](#set-up-the-qwen-code-companion-extension-for-vs-code)
  - [Set up the `GitHub Copilot Chat` extension for `VS Code`](#set-up-the-github-copilot-chat-extension-for-vs-code)
- [Check the `Qwen Code` credentials file](#check-the-qwen-code-credentials-file)
  - [Check the `Qwen Code` credentials file in the `VS Code Terminal`](#check-the-qwen-code-credentials-file-in-the-vs-code-terminal)
  - [Check the `Qwen Code` credentials file in the `VS Code Editor`](#check-the-qwen-code-credentials-file-in-the-vs-code-editor)
- [Set up the `Qwen Code` CLI (REMOTE)](#set-up-the-qwen-code-cli-remote)
- [Set up the `Qwen Code` API (REMOTE)](#set-up-the-qwen-code-api-remote)
  - [Get the `Qwen Code` API config values](#get-the-qwen-code-api-config-values)
  - [Prepare the request to the `Qwen Code` API](#prepare-the-request-to-the-qwen-code-api)
  - [Check that the `Qwen Code` API is accessible inside your VM](#check-that-the-qwen-code-api-is-accessible-inside-your-vm)
  - [Check that `Qwen Code` API is accessible from your computer](#check-that-qwen-code-api-is-accessible-from-your-computer)
- [Open a chat with `Qwen Code`](#open-a-chat-with-qwen-code)
  - [Open a chat with `Qwen Code` using the CLI](#open-a-chat-with-qwen-code-using-the-cli)
  - [Open a chat with `Qwen Code` using the `Qwen Code Companion` extension for `VS Code`](#open-a-chat-with-qwen-code-using-the-qwen-code-companion-extension-for-vs-code)
  - [Open a chat with `Qwen Code` using the `GitHub Copilot Chat` extension for `VS Code`](#open-a-chat-with-qwen-code-using-the-github-copilot-chat-extension-for-vs-code)
- [Chat with `Qwen Code`](#chat-with-qwen-code)
  - [Refer to a file](#refer-to-a-file)
  - [Use a skill](#use-a-skill)
- [Quit the chat with `Qwen Code`](#quit-the-chat-with-qwen-code)
- [Lab instructions for `Qwen Code`](#lab-instructions-for-qwen-code)

## What is `Qwen Code`

[`Qwen Code`](https://github.com/QwenLM/qwen-code) is a [coding agent](./coding-agents.md#what-is-a-coding-agent) that:

- [provides 1000 free requests per day](https://github.com/QwenLM/qwen-code#why-qwen-code) to the [`Qwen3-Coder`](https://github.com/QwenLM/Qwen3-Coder) model (see [Model](./llm.md#model)).
- is available in Russia.

See:

- [Set up the `Qwen Code` (LOCAL)](#set-up-the-qwen-code-local).
- [Set up the `Qwen Code` CLI (REMOTE)](#set-up-the-qwen-code-cli-remote).
- [Set up the `Qwen Code` API (REMOTE)](#set-up-the-qwen-code-api-remote).

## Set up the `Qwen Code` (LOCAL)

<!-- no toc -->
- Method 1: [Set up the `Qwen Code` CLI (LOCAL)](#set-up-the-qwen-code-cli-local).
- Method 2: [Set up the `Qwen Code Companion` extension for `VS Code`](#set-up-the-qwen-code-companion-extension-for-vs-code).
- Method 3: [Set up the `GitHub Copilot Chat` extension for `VS Code`](#set-up-the-github-copilot-chat-extension-for-vs-code).

### Set up the `Qwen Code` CLI (LOCAL)

> [!NOTE]
> See [CLI](./cli.md#what-is-a-cli)

1. [Install `Node.js`](./nodejs.md#install-nodejs).

2. Copy the single-line [shell command](./shell.md#shell-command) from the [installation instructions](https://github.com/QwenLM/qwen-code#installation) for [`Qwen Code`](#what-is-qwen-code).

   <!-- TODO use pnpm -->

3. [Open a chat with `Qwen Code` using the CLI](#open-a-chat-with-qwen-code-using-the-cli).

4. Write `/auth` in the chat to [authenticate via Qwen OAuth](https://github.com/QwenLM/qwen-code?tab=readme-ov-file#authentication).

5. [Check the `Qwen Code` credentials file](#check-the-qwen-code-credentials-file).

### Set up the `Qwen Code Companion` extension for `VS Code`

1. [Install the `VS Code` extension](./vs-code.md#install-the-vs-code-extension):
   `qwenlm.qwen-code-vscode-ide-companion`.

2. [Open a chat with `Qwen Code` using the `Qwen Code Companion` extension for `VS Code`](#open-a-chat-with-qwen-code-using-the-qwen-code-companion-extension-for-vs-code).

3. Write `/login` in the chat to [authenticate via Qwen OAuth](https://github.com/QwenLM/qwen-code?tab=readme-ov-file#authentication).

4. Complete the authentication procedure.

5. [Check the `Qwen Code` credentials file](#check-the-qwen-code-credentials-file).

### Set up the `GitHub Copilot Chat` extension for `VS Code`

> [!NOTE]
> `Copilot Chat` is not officially available for users in Russia (see [this discussion](https://github.com/orgs/community/discussions/182386)).

1. [Install](https://code.visualstudio.com/docs/configure/extensions/extension-marketplace#_browse-for-extensions) the `github.copilot-chat` and `denizhandaklr.vscode-qwen-copilot` extensions.

2. [Run using the `Command Palette`](./vs-code.md#run-a-command-using-the-command-palette):
   `Qwen Copilot: Authenticate` to [authenticate via Qwen OAuth](https://github.com/QwenLM/qwen-code?tab=readme-ov-file#authentication).

3. [Check the `Qwen Code` credentials file](#check-the-qwen-code-credentials-file).

4. [Run using the `Command Palette`](./vs-code.md#run-a-command-using-the-command-palette):
   `Chat: Manage Language Models`.

5. Click `Add Models`.

6. Click `Qwen Code`.

7. Double click `Qwen 3 Coder Plus` to make the model visible.

8. [Open a chat with `Qwen Code` using the `GitHub Copilot Chat` extension for `VS Code`](#open-a-chat-with-qwen-code-using-the-github-copilot-chat-extension-for-vs-code).

## Check the `Qwen Code` credentials file

- Method 1: [Check the `Qwen Code` credentials file in the `VS Code Terminal`](#check-the-qwen-code-credentials-file-in-the-vs-code-editor).
- Method 2: [Check the `Qwen Code` credentials file in the `VS Code Editor`](#check-the-qwen-code-credentials-file-in-the-vs-code-editor).

### Check the `Qwen Code` credentials file in the `VS Code Terminal`

To print the content of the credentials file,

[run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

```terminal
cat ~/.qwen/oauth_creds.json | jq .
```

### Check the `Qwen Code` credentials file in the `VS Code Editor`

[Open in `VS Code` the file](./vs-code.md#open-the-file):
`~/.qwen/oauth_creds.json`.

This file contains the `Qwen Code` authentication credentials.

The file must be non-empty.

## Set up the `Qwen Code` CLI (REMOTE)

1. [Connect to the VM](./ssh.md#connect-to-the-vm).

2. [Install `Node.js`](./nodejs.md#install-nodejs).

3. [Install `pnpm`](./nodejs.md#install-pnpm).

4. To install [`Qwen Code`](#what-is-qwen-code),

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   pnpm add -g @qwen-code/qwen-code
   ```

5. [Open a chat with `Qwen Code` using the CLI](#open-a-chat-with-qwen-code-using-the-cli).

6. Write `/auth` in the chat to [authenticate via Qwen OAuth](https://github.com/QwenLM/qwen-code?tab=readme-ov-file#authentication).

7. Open the link in a browser to complete the authentication procedure.

8. [Quit the chat with `Qwen Code`](#quit-the-chat-with-qwen-code).

## Set up the `Qwen Code` API (REMOTE)

> [`qwen-code-oai-proxy`](https://github.com/inno-se-toolkit/qwen-code-oai-proxy) exposes [`Qwen Code`](#what-is-qwen-code) through an [OpenAI-compatible API](./llm.md#openai-compatible-api) so that other tools can use it as an [LLM](./llm.md#what-is-an-llm).

<!-- TODO visualize -->

1. [Set up the `Qwen Code` CLI (REMOTE)](#set-up-the-qwen-code-cli-remote).

   Keep working in the opened `VS Code Terminal`.
   You complete the following steps on your VM.

2. To [clone using the `VS Code Terminal` the repo](./git-vscode.md#clone-the-repo-using-the-vs-code-terminal)

   <https://github.com/inno-se-toolkit/qwen-code-oai-proxy>,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   git clone https://github.com/inno-se-toolkit/qwen-code-oai-proxy ~/qwen-code-oai-proxy
   ```

3. To enter the repository directory,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cd ~/qwen-code-oai-proxy
   ```

4. To create the [environment](./environments.md#what-is-an-environment) file,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cp .env.example .env
   ```

5. To open the `.env` file in `nano`,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   nano .env
   ```

6. Write the value of `QWEN_API_KEY`.

   You'll use it in requests to the API.

7. Save the file (`Ctrl + O`).

8. To start the `Qwen Code` API,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   docker compose up --build -d
   ```

9. [Check that `Qwen Code` API is accessible inside your VM](#check-that-the-qwen-code-api-is-accessible-inside-your-vm).

10. [Check that `Qwen Code` API is accessible from your computer](#check-that-qwen-code-api-is-accessible-from-your-computer).

### Get the `Qwen Code` API config values

1. [Connect to your VM](./vm.md#connect-to-the-vm) if not yet connected.

2. To enter the repository directory,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cd ~/qwen-code-oai-proxy
   ```

3. To get the value of `HOST_PORT` in `.env`,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cat .env | grep HOST_PORT
   ```

4. To get the value of `QWEN_API_KEY` in `.env`,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cat .env | grep QWEN_API_KEY
   ```

### Prepare the request to the `Qwen Code` API

1. [Get the `Qwen Code` API config values](#get-the-qwen-code-api-config-values).

   You need `HOST_PORT` and `QWEN_API_KEY`.

2. Copy the request template to the clipboard:

   ```terminal
   curl -s http://<qwen-code-api-address>:<qwen-api-port>/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <qwen-api-key>" \
     -d '{"model":"<qwen-model>","messages":[{"role":"user","content":"What is 2+2?"}]}' \
     | jq .
   ```

3. Before you run it, replace:

   - `<qwen-api-port>` with the value of `HOST_PORT`
   - `<qwen-api-key>` with the value of `QWEN_API_KEY`
   - `<qwen-model>` with one of the available models:

     - `coder-model` — `Qwen 3.5 Plus` (recommended).
     - `qwen3-coder-plus` — `Qwen 3 Coder Plus`.
     - `qwen3-coder-flash` — `Qwen 3 Coder Flash` (faster).

4. When you run it, the output should be similar to this:

   ```terminal
   {
      "created": 1773379590,
      "usage": {
         "completion_tokens": 8,
         "prompt_tokens": 15,
         "prompt_tokens_details": {
            "cached_tokens": 0
         },
         "total_tokens": 23
      },
      "model": "qwen3-coder-plus",
      "id": "chatcmpl-9c04fd89-7d16-469f-af7b-8e64a9418bb3",
      "choices": [
         {
            "finish_reason": "stop",
            "index": 0,
            "message": {
            "role": "assistant",
            "content": "2 + 2 = 4."
            }
         }
      ],
      "object": "chat.completion"
   }
   ```

### Check that the `Qwen Code` API is accessible inside your VM

1. [Get the `Qwen Code` API config values](#get-the-qwen-code-api-config-values)

2. Stay in that `VS Code Terminal` connected to the VM.

3. [Prepare the request to the `Qwen Code` API](#prepare-the-request-to-the-qwen-code-api).

   Replace:

   - `<qwen-code-api-address>` with `localhost` because you'll run the request on your VM.

4. [Run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal)
   the prepared request.

### Check that `Qwen Code` API is accessible from your computer

1. [Get the `Qwen Code` API config values](#get-the-qwen-code-api-config-values).

2. Open a new `VS Code Terminal`.

3. [Prepare the request to the `Qwen Code` API](#prepare-the-request-to-the-qwen-code-api).

   Replace:

   - `<qwen-code-api-address>` with [`<your-vm-ip-address>`](./vm.md#your-vm-ip-address) because you'll run the request on your computer (laptop).

4. [Run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal)
   the prepared request.

## Open a chat with `Qwen Code`

<!-- no toc -->
- Method 1: [Open a chat with `Qwen Code` using the CLI](#open-a-chat-with-qwen-code-using-the-cli)
- Method 2: [Open a chat with `Qwen Code` using the `Qwen Code Companion` extension for `VS Code`](#open-a-chat-with-qwen-code-using-the-qwen-code-companion-extension-for-vs-code)
- Method 3: [Open a chat with `Qwen Code` using the `GitHub Copilot Chat` extension for `VS Code`](#open-a-chat-with-qwen-code-using-the-github-copilot-chat-extension-for-vs-code)

### Open a chat with `Qwen Code` using the CLI

> [!NOTE]
> See [CLI](./cli.md#what-is-a-cli).

1. [Run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   qwen
   ```

   See [Quit the chat with `Qwen Code`](#quit-the-chat-with-qwen-code).

### Open a chat with `Qwen Code` using the `Qwen Code Companion` extension for `VS Code`

Method 1:

1. Go to the [`Editor Toolbar`](./vs-code.md#editor-toolbar).
2. Click the `Qwen Code: Open` icon.

   <img alt="Icon Qwen Code: Open" src="./images/qwen-code/qwen-code-open.png" style="width:300px"></img>

Method 2:

1. [Run using the `Command Palette`](./vs-code.md#run-a-command-using-the-command-palette):
   `Qwen Code: Open`.

### Open a chat with `Qwen Code` using the `GitHub Copilot Chat` extension for `VS Code`

1. [Run using the `Command Palette`](./vs-code.md#run-a-command-using-the-command-palette):
   `Chat: Open Chat`
2. The `CHAT` panel will open.
3. Go to `CHAT`.
4. Click `Auto` (`Pick Model`).
5. Click `Qwen 3 Coder Plus`.

## Chat with `Qwen Code`

Actions:

<!-- no toc -->
- [Refer to a file](#refer-to-a-file)
- [Use a skill](#use-a-skill)

### Refer to a file

Write `@<file-path>` (without `<` and `>`) to refer to the file at the [`<file-path>`](./file-system.md#file-path-placeholder).

Example: `@main.py`.

### Use a skill

1. [Open a chat with `Qwen Code`](#open-a-chat-with-qwen-code).
2. Write `skills`.
3. Press `Enter`.
4. To use the skill, write the [skill name](./coding-agents.md#skill-name) and the [skill arguments](./coding-agents.md#skill-arguments).

   Example: `commit @main.py`.

   See [Refer to a file](#refer-to-a-file).
5. Press `Enter`.

## Quit the chat with `Qwen Code`

1. Write `/quit`.
2. Press `Enter`.

## Lab instructions for `Qwen Code`

[`Qwen Code`](#what-is-qwen-code) automatically reads [`AGENTS.md`](../AGENTS.md) in the project root. This file contains instructions that guide the agent to help you learn — not just generate code. The agent will ask you questions, help you plan, and encourage you to write code yourself.
