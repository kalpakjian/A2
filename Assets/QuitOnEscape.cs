using UnityEngine;

/// <summary>
/// 按下 ESC 鍵離開遊戲。
/// 在 Unity Editor 中執行時，ESC 會停止 Play Mode；
/// 在正式 Build 中，ESC 會呼叫 Application.Quit() 關閉程式。
/// </summary>
public class QuitOnEscape : MonoBehaviour
{
    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Escape))
        {
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#else
            Application.Quit();
#endif
        }
    }
}
