import { useState } from 'react'
import {
  ThumbsUp,
  MessageCircle,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react'

export default function CommentSection() {

  const [comment, setComment] = useState('')

  const [posts, setPosts] = useState([])

  const handleSubmit = () => {

    if (!comment.trim()) return

    const newPost = {
      id: Date.now(),
      text: comment,
      likes: 0,
      category: 'Citizen Discussion',
      time: 'Just now',
    }

    setPosts([newPost, ...posts])

    setComment('')
  }

  const handleLike = (id) => {

    const updated = posts
      .map((post) =>
        post.id === id
          ? { ...post, likes: post.likes + 1 }
          : post
      )
      .sort((a, b) => b.likes - a.likes)

    setPosts(updated)
  }

  return (
    <div className="comment-section">

      <div className="discussion-header">

        <div>

          <h3>Citizen Discussion</h3>

          <p className="comment-subtitle">
            Citizens can anonymously discuss projects,
            ask questions, and raise accountability concerns.
          </p>

        </div>

        <div className="anonymous-badge">

          <ShieldCheck size={18} />

          Anonymous Protected

        </div>

      </div>

      <div className="comment-box">

        <textarea
          className="comment-input"
          placeholder="Share your concern, project observation, or accountability question..."
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />

        <button
          className="comment-btn"
          onClick={handleSubmit}
        >

          <MessageCircle size={18} />

          Publish Discussion

        </button>

      </div>

      <div className="discussion-feed">

        {posts.length === 0 ? (

          <div className="empty-discussion">

            No public discussions yet.
            Be the first citizen to raise a concern.

          </div>

        ) : (

          posts.map((post) => (

            <div
              key={post.id}
              className="comment-card"
            >

              <div className="comment-top">

                <div className="comment-category">

                  {post.category}

                </div>

                <div className="comment-time">

                  {post.time}

                </div>

              </div>

              <div className="anonymous-user">

                Anonymous Citizen

              </div>

              <p className="comment-text">

                {post.text}

              </p>

              <div className="comment-actions">

                <button
                  className="reaction-btn"
                  onClick={() => handleLike(post.id)}
                >

                  <ThumbsUp size={16} />

                  {post.likes}

                </button>

                <div className="trending-tag">

                  <TrendingUp size={15} />

                  Public Interest

                </div>

              </div>

            </div>
          ))
        )}

      </div>

    </div>
  )
}