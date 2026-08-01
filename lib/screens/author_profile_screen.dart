import 'package:flutter/material.dart';

class AuthorProfileScreen extends StatelessWidget {
  const AuthorProfileScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    const String assetImagePath = "assets/images/author_photo.jpg";

    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Center(
              child: Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: Colors.white.withOpacity(0.2),
                    width: 3,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.5),
                      blurRadius: 15,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: const CircleAvatar(
                  radius: 75,
                  backgroundColor: Colors.grey,
                  backgroundImage: AssetImage(assetImagePath),
                ),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              "CHRISHEM",
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.5,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              "App Creator & Lead Developer",
              style: TextStyle(
                fontSize: 15,
                color: Colors.white.withOpacity(0.6),
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              "Chrishem is an innovative software engineer passionate about creating intuitive user experiences. "
              "With expertise in mobile development and data systems, he brings ideas to life through code.",
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                height: 1.5,
                color: Colors.white.withOpacity(0.8),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
