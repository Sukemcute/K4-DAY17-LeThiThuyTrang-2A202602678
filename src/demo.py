"""Small runnable demo; all personal facts below are synthetic."""
from agent_baseline import BaselineAgent
from agent_advanced import AdvancedAgent
from config import load_config

def main():
    config = load_config()
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    user = 'demo_trang'
    statements = [
        'Mình tên là Trang. Mình sống ở Huế. Mình đang làm backend engineer.',
        'Mình muốn bạn trả lời ngắn gọn thành 3 bullet, có ví dụ thực chiến.',
        'Mình không còn làm backend engineer nữa, giờ chuyển sang MLOps engineer.',
        'Giờ mình đang ở Hải Phòng chứ không còn ở Huế nữa.',
        'Mình đùa là chuyển sang product manager. Hà Nội chỉ là nơi đi họp.',
    ]
    for agent in (baseline, advanced):
        for message in statements:
            agent.reply(user, 'demo-train', message)
    question = 'Tên, nghề nghiệp hiện tại, nơi ở hiện tại và style trả lời mình thích là gì?'
    print('BASELINE / THREAD MỚI:')
    print(baseline.reply(user, 'demo-recall', question)['response'])
    print('\nADVANCED / THREAD MỚI:')
    print(advanced.reply(user, 'demo-recall', question)['response'])
    restarted = AdvancedAgent(config, force_offline=True)
    print('\nADVANCED / KHỞI TẠO LẠI:')
    print(restarted.reply(user, 'demo-restart', question)['response'])
    print('\nProfile:', advanced.profile_store.path_for(user))

if __name__ == '__main__':
    main()
