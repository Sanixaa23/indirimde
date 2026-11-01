package com.indirimde.app.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Apple system hues, matching the backend/hotkeyd palette.
val Blue = Color(0xFF007AFF)
val Green = Color(0xFF34C759)
val Red = Color(0xFFFF3B30)
val Amber = Color(0xFFFF9F0A)
val Gray = Color(0xFF8E8E93)
val Ink = Color(0xFF1C1C1E)
val Ink2 = Color(0xFF54545A)

// Soft "frost" background stops for the glass look.
val FrostTop = Color(0xFFEAF1FB)
val FrostBottom = Color(0xFFF6F7FB)
val GlassWhite = Color(0xE6FFFFFF)   // ~0.90 — the one near-solid surface
val GlassHairline = Color(0x141C1C1E) // ~0.08 ink

private val LightColors = lightColorScheme(
    primary = Blue,
    onPrimary = Color.White,
    secondary = Green,
    background = FrostBottom,
    onBackground = Ink,
    surface = GlassWhite,
    onSurface = Ink,
    error = Red,
)

private val DarkColors = darkColorScheme(
    primary = Blue,
    secondary = Green,
    error = Red,
)

@Composable
fun IndirimdeTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        typography = Typography(),
        content = content,
    )
}
