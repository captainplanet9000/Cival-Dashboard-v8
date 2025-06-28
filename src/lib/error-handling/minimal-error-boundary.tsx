'use client'

import React, { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: ErrorInfo
}

class MinimalErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  }

  public static getDerivedStateFromError(_: Error): State {
    return { hasError: true }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Minimal Error Boundary caught an error:', error, errorInfo)
    this.setState({ error, errorInfo })
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            fontFamily:
              'system-ui, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji"',
            height: '100vh',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div style={{ lineHeight: '48px' }}>
            <style
              dangerouslySetInnerHTML={{
                __html:
                  'body{color:#000;background:#fff;margin:0}.next-error-h1{border-right:1px solid rgba(0,0,0,.3)}@media (prefers-color-scheme:dark){body{color:#fff;background:#000}.next-error-h1{border-right:1px solid rgba(255,255,255,.3)}}',
              }}
            />
            <h1
              className="next-error-h1"
              style={{
                display: 'inline-block',
                margin: '0 20px 0 0',
                padding: '0 23px 0 0',
                fontSize: '24px',
                fontWeight: 500,
                verticalAlign: 'top',
              }}
            >
              Error
            </h1>
            <div
              style={{
                display: 'inline-block',
                textAlign: 'left',
                lineHeight: '49px',
                height: '49px',
                verticalAlign: 'middle',
              }}
            >
              <h2 style={{ fontSize: '14px', fontWeight: 400, lineHeight: '49px', margin: 0 }}>
                An error occurred. We are working on it.
              </h2>
            </div>
            {this.state.error && (
              <details style={{ marginTop: '20px', textAlign: 'left', fontSize: '12px', whiteSpace: 'pre-wrap' }}>
                <summary>Error Details</summary>
                <p>{this.state.error.toString()}</p>
                {this.state.errorInfo && <p>{this.state.errorInfo.componentStack}</p>}
              </details>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default MinimalErrorBoundary
