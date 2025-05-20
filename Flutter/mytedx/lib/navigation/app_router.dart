import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:mytedx/data/models/talk.dart';
import 'package:mytedx/presentation/screens/home_screen.dart';
import 'package:mytedx/presentation/screens/talks_by_tag_screen.dart';
import 'package:mytedx/presentation/screens/talk_detail_screen.dart';
import 'package:mytedx/presentation/screens/global_search_screen.dart';

class AppRouter {
  static const String homeRoute = '/';
  static const String talksByTagRoute = '/tag'; // /tag/:tagname
  static const String talkDetailRoute =
      '/talk'; // /talk/:talkId (talkId è lo slug o l'id univoco)
  static const String globalSearchRoute = '/search';

  static final GoRouter router = GoRouter(
    initialLocation: homeRoute,
    routes: <RouteBase>[
      GoRoute(
        path: homeRoute,
        builder:
            (BuildContext context, GoRouterState state) => const HomeScreen(),
      ),
      GoRoute(
        path: '$talksByTagRoute/:tag', // es: /tag/technology
        builder: (BuildContext context, GoRouterState state) {
          final tag = state.pathParameters['tag']!;
          return TalksByTagScreen(tag: tag);
        },
      ),
      GoRoute(
        path: '$talkDetailRoute/:talkId', // es: /talk/some-talk-slug
        builder: (BuildContext context, GoRouterState state) {
          final talkId = state.pathParameters['talkId']!;
          final talk = state.extra as Talk?; // Riceve l'oggetto Talk completo

          // Se talk non è passato via extra, idealmente dovremmo avere un modo per caricarlo qui
          // basandoci su talkId. Per ora, assumiamo che sia sempre passato.
          if (talk == null) {
            // Potresti mostrare un errore o reindirizzare, o avere un provider che carica il talk by id.
            // Per ora, questo scenario implica un errore di programmazione nel chiamare la route.
            return Scaffold(
              appBar: AppBar(title: const Text("Error")),
              body: const Center(
                child: Text("Talk data not provided to detail screen."),
              ),
            );
          }
          return TalkDetailScreen(talk: talk);
        },
      ),
      GoRoute(
        path: globalSearchRoute,
        builder:
            (BuildContext context, GoRouterState state) =>
                const GlobalSearchScreen(),
      ),
    ],
    errorBuilder:
        (context, state) => Scaffold(
          appBar: AppBar(title: const Text('Page Not Found')),
          body: Center(child: Text('Error: ${state.error?.message}')),
        ),
  );
}
