import 'package:flutter/material.dart';
import 'package:dio/dio.dart'; // Per chiamate API
import 'dart:convert'; // Per jsonEncode/jsonDecode
import 'package:intl/intl.dart'; // Per formattazione data

import 'package:mytedx/core/utils/debouncer.dart';
import 'package:mytedx/presentation/widgets/common_widgets.dart';
import 'package:mytedx/navigation/app_router.dart';
import 'package:go_router/go_router.dart';
import 'package:mytedx/data/models/talk.dart'; // Per il modello Talk completo
// Assumi che SearchedTalk sia accessibile. Se è in un file separato, importalo:
// import 'package:mytedx/data/models/searched_talk.dart'; // Adatta il percorso

// --------------- INIZIO MODELLO SearchedTalk (se non in file separato) ---------------
// Se hai SearchedTalk in un file separato, rimuovi questa sezione e importalo.
class SearchedTalk {
  final String id;
  final String title;
  final String details;
  final String slug;
  final String mainSpeaker;
  final String url;
  final List<String> tags;
  final String? publishedAt;
  final int? duration;

  SearchedTalk({
    required this.id,
    required this.title,
    required this.details,
    required this.slug,
    required this.mainSpeaker,
    required this.url,
    required this.tags,
    this.publishedAt,
    this.duration,
  });

  factory SearchedTalk.fromJSON(Map<String, dynamic> jsonMap) {
    String determineId(Map<String, dynamic> map) {
      if (map['id'] != null) return map['id'].toString();
      return DateTime.now().millisecondsSinceEpoch.toString();
    }
    List<String> parseTags(dynamic tagsData) {
      if (tagsData is List) return tagsData.map((tag) => tag.toString()).toList();
      return [];
    }
    int? parseDuration(dynamic durationData) {
      if (durationData is int) return durationData;
      if (durationData is String) return int.tryParse(durationData);
      return null;
    }
    return SearchedTalk(
      id: determineId(jsonMap),
      title: jsonMap['title']?.toString() ?? 'No Title',
      details: jsonMap['description']?.toString() ?? 'No Description',
      slug: jsonMap['slug']?.toString() ?? '',
      mainSpeaker: jsonMap['speakers']?.toString() ?? 'Unknown Speaker',
      url: jsonMap['url']?.toString() ?? '',
      tags: parseTags(jsonMap['tags']),
      publishedAt: jsonMap['publishedAt']?.toString(),
      duration: parseDuration(jsonMap['duration']),
    );
  }
}
// --------------- FINE MODELLO SearchedTalk ---------------


class GlobalSearchScreen extends StatefulWidget { // Cambiato a StatefulWidget
  const GlobalSearchScreen({super.key});

  @override
  State<GlobalSearchScreen> createState() => _GlobalSearchScreenState();
}

class _GlobalSearchScreenState extends State<GlobalSearchScreen> {
  final _searchController = TextEditingController();
  final _debouncer = Debouncer(milliseconds: 500);
  final Dio _dio = Dio(); // Istanza di Dio per le chiamate API

  // Stato interno per la query, i risultati, il caricamento e l'errore
  String _currentQuery = '';
  List<SearchedTalk> _searchResults = [];
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(() {
      _debouncer.run(() {
        if (mounted) {
          final newQuery = _searchController.text;
          if (_currentQuery != newQuery) {
            setState(() {
              _currentQuery = newQuery;
            });
            _fetchSearchResults();
          }
        }
      });
    });
  }

  Future<void> _fetchSearchResults() async {
    if (_currentQuery.trim().isEmpty || _currentQuery.trim().length < 3) {
      setState(() {
        _searchResults = [];
        _isLoading = false;
        _errorMessage = null;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    // Sostituisci con il tuo URL effettivo dell'API Lambda
    const String apiUrl = "https://fjpcr39w76.execute-api.us-east-1.amazonaws.com/default/search-by-title";

    try {
      final response = await _dio.post(
        apiUrl,
        data: jsonEncode({'search': _currentQuery}),
        options: Options(headers: {'Content-Type': 'application/json'}),
      );

      if (response.statusCode == 200) {
        final List<dynamic> jsonData = response.data;
        if (mounted) {
          setState(() {
            _searchResults = jsonData
                .map((item) => SearchedTalk.fromJSON(item as Map<String, dynamic>))
                .toList();
            _isLoading = false;
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _errorMessage = 'Failed to load results: ${response.statusMessage}';
            _isLoading = false;
            _searchResults = [];
          });
        }
      }
    } on DioException catch (e) {
        if (mounted) {
            String errorMsg = 'Network error or invalid URL';
            if (e.response != null && e.response?.data is Map) {
                errorMsg = e.response?.data['error'] ?? e.message ?? 'Failed to load search results (Dio)';
            } else if (e.message != null){
                errorMsg = e.message!;
            }
            setState(() {
                _errorMessage = errorMsg;
                _isLoading = false;
                _searchResults = [];
            });
        }
    } 
    catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'An unexpected error occurred: $e';
          _isLoading = false;
          _searchResults = [];
        });
      }
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    _debouncer.dispose();
    super.dispose();
  }

  String _formatDuration(int? totalSeconds) {
    if (totalSeconds == null || totalSeconds <= 0) return '';
    final duration = Duration(seconds: totalSeconds);
    final minutes = duration.inMinutes;
    final seconds = totalSeconds % 60;
    if (minutes == 0) return '$seconds sec';
    if (seconds == 0) return '$minutes min';
    return '$minutes min $seconds sec';
  }

  String _formatPublishedDate(String? isoDateString) {
    if (isoDateString == null || isoDateString.isEmpty) return '';
    try {
      final dateTime = DateTime.parse(isoDateString);
      return DateFormat.yMMMd().format(dateTime);
    } catch (e) {
      return isoDateString;
    }
  }

  Widget _buildBodyContent() {
    if (_currentQuery.trim().isEmpty || _currentQuery.trim().length < 3) {
      return const EmptyContent(
        message: 'Enter at least 3 characters to search.',
        icon: Icons.search_off_outlined,
      );
    }

    if (_isLoading) {
      return const AppLoader();
    }

    if (_errorMessage != null) {
      return ErrorDisplay(
        message: _errorMessage!,
        onRetry: _fetchSearchResults,
      );
    }

    if (_searchResults.isEmpty) {
      return EmptyContent(
        message: 'No talks found for "$_currentQuery".',
      );
    }

    final theme = Theme.of(context);
    final textTheme = theme.textTheme;

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
      itemCount: _searchResults.length,
      itemBuilder: (context, index) {
        final searchedTalk = _searchResults[index];
        return Card(
          elevation: 2,
          margin: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 8.0),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () {
              final talkForDetail = Talk(
                id: searchedTalk.id,
                title: searchedTalk.title,
                details: searchedTalk.details,
                slug: searchedTalk.slug.isNotEmpty ? searchedTalk.slug : searchedTalk.id,
                mainSpeaker: searchedTalk.mainSpeaker,
                url: searchedTalk.url,
                publishedAt: searchedTalk.publishedAt, // Assumendo Talk.publishedAt sia String?
                duration: searchedTalk.duration,
              );
              context.push(
                '${AppRouter.talkDetailRoute}/${searchedTalk.id}',
                extra: talkForDetail,
              );
            },
            child: Padding(
              padding: const EdgeInsets.all(12.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    searchedTalk.title,
                    style: textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.primary,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 6),
                  if (searchedTalk.mainSpeaker.isNotEmpty)
                    Row(
                      children: [
                        Icon(Icons.person_outline, size: 16, color: theme.colorScheme.secondary),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            searchedTalk.mainSpeaker,
                            style: textTheme.bodySmall,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  const SizedBox(height: 4),
                  Text(
                    searchedTalk.details,
                    style: textTheme.bodyMedium,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      if (searchedTalk.duration != null && searchedTalk.duration! > 0)
                        Row(
                          children: [
                            Icon(Icons.timer_outlined, size: 14, color: textTheme.bodySmall?.color?.withOpacity(0.7)),
                            const SizedBox(width: 4),
                            Text(_formatDuration(searchedTalk.duration), style: textTheme.bodySmall),
                          ],
                        ),
                      if (searchedTalk.publishedAt != null && searchedTalk.publishedAt!.isNotEmpty)
                        Row(
                          children: [
                            Icon(Icons.calendar_today_outlined, size: 14, color: textTheme.bodySmall?.color?.withOpacity(0.7)),
                            const SizedBox(width: 4),
                            Text(_formatPublishedDate(searchedTalk.publishedAt), style: textTheme.bodySmall),
                          ],
                        ),
                    ],
                  ),
                  if (searchedTalk.tags.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 6.0,
                      runSpacing: 4.0,
                      children: searchedTalk.tags.map((tag) {
                        return Chip(
                          label: Text(tag, style: textTheme.labelSmall),
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 0),
                          backgroundColor: theme.colorScheme.secondaryContainer.withOpacity(0.7),
                          labelStyle: TextStyle(color: theme.colorScheme.onSecondaryContainer),
                          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        );
                      }).toList(),
                    ),
                  ]
                ],
              ),
            ),
          ),
        );
      },
    );
  }


  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Search Talks by Title (Local State)')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: TextField(
              controller: _searchController,
              autofocus: true,
              decoration: InputDecoration(
                hintText: 'Enter talk title...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          // Resetta lo stato della ricerca quando il campo viene pulito
                           setState(() {
                            _currentQuery = '';
                            _searchResults = [];
                            _isLoading = false;
                            _errorMessage = null;
                          });
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(25.0),
                  borderSide: BorderSide.none,
                ),
                filled: true,
                fillColor: theme.colorScheme.surfaceVariant.withOpacity(0.5),
              ),
            ),
          ),
          Expanded(child: _buildBodyContent()),
        ],
      ),
    );
  }
}