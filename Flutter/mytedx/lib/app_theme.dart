import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const Color primaryColor = Color(0xFFE62B1E); // TED Red
  static const Color accentColor = Color(0xFF4A4A4A); // Dark Grey
  static const Color backgroundColor = Color(0xFFFFFFFF); // White
  static const Color surfaceColor = Color(0xFFF5F5F5); // Light Grey
  static const Color onPrimaryColor = Colors.white;
  static const Color onAccentColor = Colors.white;
  static const Color onBackgroundColor = Colors.black;
  static const Color onSurfaceColor = Colors.black;
  static const Color errorColor = Color(0xFFD32F2F);

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      primaryColor: primaryColor,
      scaffoldBackgroundColor: backgroundColor,
      colorScheme: const ColorScheme(
        brightness: Brightness.light,
        primary: primaryColor,
        onPrimary: onPrimaryColor,
        secondary: accentColor,
        onSecondary: onAccentColor,
        error: errorColor,
        onError: Colors.white,
        surface: surfaceColor, // Usato per Card, Dialog background etc. in M3
        onSurface: onSurfaceColor, // Testo/icone su surface
        surfaceContainerHighest: backgroundColor, // Sfondo principale
        onSurfaceVariant:
            accentColor, // Per elementi meno prominenti su surface
      ),
      textTheme: GoogleFonts.latoTextTheme(
        ThemeData.light().textTheme,
      ).copyWith(
        displayLarge: GoogleFonts.montserrat(
          fontSize: 28,
          fontWeight: FontWeight.bold,
          color: onBackgroundColor,
        ),
        displayMedium: GoogleFonts.montserrat(
          fontSize: 24,
          fontWeight: FontWeight.bold,
          color: onBackgroundColor,
        ),
        headlineMedium: GoogleFonts.montserrat(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: onBackgroundColor,
        ),
        titleLarge: GoogleFonts.lato(
          fontSize: 18,
          fontWeight: FontWeight.bold,
          color: onBackgroundColor,
        ),
        titleMedium: GoogleFonts.lato(
          fontSize: 16,
          fontWeight: FontWeight.w500,
          color: onSurfaceColor,
        ),
        bodyLarge: GoogleFonts.lato(fontSize: 16, color: onSurfaceColor),
        bodyMedium: GoogleFonts.lato(fontSize: 14, color: onSurfaceColor),
        labelLarge: GoogleFonts.lato(
          fontSize: 16,
          fontWeight: FontWeight.bold,
          color: onPrimaryColor,
        ), // Per testo su bottoni
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: primaryColor,
        foregroundColor: onPrimaryColor, // Colore icone e testo AppBar
        elevation: 2,
        titleTextStyle: GoogleFonts.montserrat(
          fontSize: 20,
          fontWeight: FontWeight.bold,
          color: onPrimaryColor,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: onPrimaryColor,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          textStyle: GoogleFonts.lato(
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: accentColor),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: primaryColor, width: 2),
        ),
        labelStyle: GoogleFonts.lato(color: accentColor),
        hintStyle: GoogleFonts.lato(color: accentColor.withOpacity(0.7)),
      ),
      cardTheme: CardThemeData(
        elevation: 1,
        margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 0),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        color: surfaceColor, // deve essere una variabile, non const
      ),
      listTileTheme: ListTileThemeData(
        iconColor: primaryColor,
        titleTextStyle: GoogleFonts.lato(
          fontSize: 16,
          fontWeight: FontWeight.w500,
          color: onSurfaceColor,
        ),
        subtitleTextStyle: GoogleFonts.lato(fontSize: 14, color: accentColor),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: primaryColor,
        foregroundColor: onPrimaryColor,
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: primaryColor,
      ),
    );
  }

  // Puoi definire un tema scuro se vuoi
  // static ThemeData get darkTheme { ... }
}
