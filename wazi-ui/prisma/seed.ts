import 'dotenv/config';
import { prisma } from '../lib/prisma';

async function main() {
  await prisma.project.deleteMany();
  await prisma.county.deleteMany();

  const counties = await Promise.all(
    ['Nairobi', 'Mombasa', 'Kiambu'].map((name) =>
      prisma.county.create({
        data: { name },
      }),
    ),
  );

  await prisma.project.createMany({
    data: [
      { title: 'Water network expansion', status: 'in-progress', countyId: counties[0].id },
      { title: 'Primary school rehabilitation', status: 'planned', countyId: counties[1].id },
      { title: 'Road maintenance works', status: 'completed', countyId: counties[2].id },
    ],
  });
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (error) => {
    console.error(error);
    await prisma.$disconnect();
    process.exit(1);
  });