import 'dart:convert';
import 'dart:math';
import 'package:http/http.dart' as http;
import 'package:mytedx/core/constants/api_constants.dart';
import 'package:mytedx/data/models/talk.dart';
import 'package:mytedx/data/models/related_talk.dart';
import 'package:mytedx/data/models/searched_talk.dart';
import 'package:mytedx/data/models/talk_summary.dart';

class TalkApiService {
  final http.Client _client;

  TalkApiService({http.Client? client}) : _client = client ?? http.Client();

  Future<List<String>> getAvailableTags() async {
    final url = Uri.parse(ApiConstants.getAvailableTags);
    try {
      final response = await _client.get(
        url,
        headers: {'Accept': 'application/json'},
      );

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(
          utf8.decode(response.bodyBytes),
        );
        return List<String>.from(jsonList);
      } else {
        print('Failed to load tags: ${response.statusCode} ${response.body}');
        throw Exception('Failed to load tags. Status: ${response.statusCode}');
      }
    } catch (e) {
      print('Error in getAvailableTags: $e');
      throw Exception('Network error or server issue: $e');
    }
  }

  Future<String> getRandomTag() async {
    try {
      final tags = await getAvailableTags();

      if (tags.isEmpty) {
        throw Exception('No tags available.');
      }

      final random = Random();
      final randomTag = tags[random.nextInt(tags.length)];

      print('Random tag selected: $randomTag');

      return randomTag;
    } catch (e) {
      print('Error in getRandomTag: $e');
      throw Exception('Could not fetch a random tag: $e');
    }
  }

  Future<List<Talk>> getTalksByTag(String tag, int page) async {
    final url = Uri.parse(ApiConstants.getTalksByTagEndpoint);
    try {
      final response = await _client.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'tags': tag,
        }),
      );

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(
          utf8.decode(response.bodyBytes),
        );
        return jsonList.map((json) => Talk.fromJSON(json)).toList();
      } else {
        print(
          'Failed to load talks by tag: ${response.statusCode} ${response.body}',
        );
        throw Exception(
          'Failed to load talks by tag. Status: ${response.statusCode}',
        );
      }
    } catch (e) {
      print('Error in getTalksByTag: $e');
      throw Exception('Network error or server issue: $e');
    }
  }

  Future<TalkSummary> getTalkSummary(String talkId) async {
    // La tua lambda Get_Talk_Summary_HuggingFace accetta 'id' in queryStringParameters, pathParameters o body.
    // Usiamo queryStringParameters per semplicità con GET. Se la tua API Gateway è configurata per POST, adatta.
    final url = Uri.parse('${ApiConstants.getTalkSummaryEndpoint}?id=$talkId');
    try {
      // Assumiamo che la Lambda sia esposta via GET, o POST con id nel body.
      // Se è POST con 'id' nel body JSON:
      // final response = await _client.post(
      //   Uri.parse(ApiConstants.getTalkSummaryEndpoint),
      //   headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      //   body: jsonEncode({'id': talkId}),
      // );
      // Se è GET con 'id' come query parameter:
      final response = await _client.get(
        url,
        headers: {'Accept': 'application/json'},
      );

      if (response.statusCode == 200) {
        final Map<String, dynamic> jsonMap = json.decode(
          utf8.decode(response.bodyBytes),
        );
        return TalkSummary.fromJSON(jsonMap);
      } else {
        print(
          'Failed to load talk summary: ${response.statusCode} ${response.body}',
        );
        throw Exception(
          'Failed to load talk summary. Status: ${response.statusCode}',
        );
      }
    } catch (e) {
      print('Error in getTalkSummary: $e');
      throw Exception('Network error or server issue: $e');
    }
  }

  Future<List<RelatedTalk>> getRelatedTalks(String talkId) async {
    // Simile a getTalkSummary, assumiamo GET con 'id' come query parameter.
    final url = Uri.parse('${ApiConstants.getRelatedTalksEndpoint}?id=$talkId');
    try {
      final response = await _client.get(
        url,
        headers: {'Accept': 'application/json'},
      );

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(
          utf8.decode(response.bodyBytes),
        );
        return jsonList.map((json) => RelatedTalk.fromJSON(json)).toList();
      } else {
        print(
          'Failed to load related talks: ${response.statusCode} ${response.body}',
        );
        throw Exception(
          'Failed to load related talks. Status: ${response.statusCode}',
        );
      }
    } catch (e) {
      print('Error in getRelatedTalks: $e');
      throw Exception('Network error or server issue: $e');
    }
  }

  Future<List<SearchedTalk>> searchTalksByTitle(String searchTerm) async {
    // La tua lambda Search_Nodes_By_Title_Neo4j si aspetta 'search' nel body di un POST.
    final url = Uri.parse(ApiConstants.searchTalksByTitleEndpoint);
    try {
      final response = await _client.post(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode({'search': searchTerm}),
      );

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(
          utf8.decode(response.bodyBytes),
        );
        return jsonList.map((json) => SearchedTalk.fromJSON(json)).toList();
      } else {
        print(
          'Failed to search talks: ${response.statusCode} ${response.body}',
        );
        throw Exception(
          'Failed to search talks. Status: ${response.statusCode}',
        );
      }
    } catch (e) {
      print('Error in searchTalksByTitle: $e');
      throw Exception('Network error or server issue: $e');
    }
  }
}
